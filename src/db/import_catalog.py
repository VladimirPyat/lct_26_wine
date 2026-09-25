"""CLI: import prepared ready+additional CSVs into Compose Postgres.

Usage (from repo root)::

    uv run python -m db.import_catalog --crop-first --recreate-wines

Copies full-bottle images to ``static/wines/`` (UI only). Embeddings come from
YOLO label crops under ``data/tmp/catalog_crops/``. Failed/small crops go to
``data/tmp/catalog_crops_review/`` and are not inserted.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import shutil
import sys
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from PIL import Image
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from core.config import AppSettings, load_app_settings
from core.cropper.onnx_yolo import OnnxYoloCropper, create_label_cropper
from core.retrieve.dino_encoder import DinoOnnxEncoder, create_dino_encoder
from db.models import Category, Region, SweetnessLevel, Wine
from db.repository import WineRepository
from db.session import create_session_factory

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SENTINEL = "н/д"

# Canonical sweetness names (longest first for token match).
_SWEETNESS_TOKENS: tuple[str, ...] = tuple(
    sorted(
        ("сухое", "полусухое", "полусладкое", "сладкое", "брют", "экстра брют"),
        key=len,
        reverse=True,
    )
)

_WORD_BOUNDARY = re.compile(r"[^\w]+", re.UNICODE)

_REVIEW_REASONS_HEADER = ("slug", "reason", "source_path", "crop_wh")


def _text_or_sentinel(value: str | None) -> str:
    text = (value or "").strip()
    return text if text else _SENTINEL


def get_or_create_category(session: Session, name: str) -> Category:
    row = session.scalars(select(Category).where(Category.name == name)).one_or_none()
    if row is not None:
        return row
    row = Category(name=name)
    session.add(row)
    session.flush()
    return row


def get_or_create_region(session: Session, name: str) -> Region:
    row = session.scalars(select(Region).where(Region.name == name)).one_or_none()
    if row is not None:
        return row
    row = Region(name=name)
    session.add(row)
    session.flush()
    return row


def get_or_create_sweetness(session: Session, name: str) -> SweetnessLevel:
    row = session.scalars(
        select(SweetnessLevel).where(SweetnessLevel.name == name)
    ).one_or_none()
    if row is not None:
        return row
    row = SweetnessLevel(name=name)
    session.add(row)
    session.flush()
    return row


def match_sweetness_token(category: str | None) -> str | None:
    """Case-insensitive exact token match; longest token wins."""
    if not category:
        return None
    lowered = category.casefold()
    normalized = _WORD_BOUNDARY.sub(" ", lowered).strip()
    padded = f" {normalized} "
    for token in _SWEETNESS_TOKENS:
        needle = f" {token.casefold()} "
        if needle in padded:
            return token
    return None


def _parse_dishes_cell(raw: str | None) -> list[str] | None:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError:
        return [part.strip() for part in text.split(",") if part.strip()] or None
    if isinstance(loaded, list):
        dishes = [str(item).strip() for item in loaded if str(item).strip()]
        return dishes or None
    return None


def _parse_optional_float(raw: str | None) -> float | None:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_optional_decimal(raw: str | None) -> Decimal | None:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        value = Decimal(text.replace(",", "."))
    except InvalidOperation:
        return None
    if value > 35:
        return None
    return value


def _load_site_categories(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        return {}
    out: dict[str, str] = {}
    for item in payload:
        if not isinstance(item, dict):
            continue
        slug = str(item.get("slug") or "").strip()
        if not slug:
            continue
        cat = item.get("category")
        out[slug] = "" if cat is None else str(cat)
    return out


def _read_csv_rows(paths: Sequence[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        if not path.is_file():
            logger.warning("CSV missing, skip: %s", path)
            continue
        with path.open(encoding="utf-8", newline="") as handle:
            rows.extend(list(csv.DictReader(handle)))
    return rows


def resolve_source_image(
    row: Mapping[str, str],
    *,
    owner_images: Path,
    site_images: Path,
) -> Path | None:
    """Resolve on-disk source file from prepare CSV columns."""
    source_image = (row.get("source_image") or "").strip()
    image_source = (row.get("image_source") or "").strip().lower()
    if not source_image:
        return None
    if image_source == "site":
        path = site_images / source_image
    else:
        path = owner_images / source_image
    return path if path.is_file() else None


def copy_catalog_image(source: Path, dest: Path) -> None:
    """Copy/convert image to ``dest`` (prefer WebP)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() == ".webp" and dest.suffix.lower() == ".webp":
        shutil.copy2(source, dest)
        return
    with Image.open(source) as image:
        image.save(dest, format="WEBP", quality=90)


def _resolve_under_root(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else _REPO_ROOT / path


def wipe_wines(session: Session) -> int:
    """Hard-delete all wine rows; keep sweetness/category/region seeds."""
    result = session.execute(delete(Wine))
    session.commit()
    deleted = int(result.rowcount or 0)
    logger.info("recreate-wines: deleted %s wine rows", deleted)
    return deleted


def run_catalog_crop_pass(
    rows: Sequence[Mapping[str, str]],
    *,
    owner_images: Path,
    site_images: Path,
    crops_dir: Path,
    review_dir: Path,
    cropper: OnnxYoloCropper,
    min_crop_side: int,
    progress_every: int = 50,
) -> dict[str, int]:
    """YOLO-crop each catalog source; OK → crops_dir, else → review_dir + reasons."""
    crops_dir.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)
    reasons_path = review_dir / "reasons.csv"

    stats: dict[str, int] = {
        "seen": 0,
        "ok": 0,
        "review": 0,
        "skipped_missing_slug": 0,
        "skipped_missing_image": 0,
        "reason_no_box": 0,
        "reason_empty_crop": 0,
        "reason_too_small": 0,
        "reason_write_fail": 0,
        "reason_read_fail": 0,
        "reason_other": 0,
    }

    with reasons_path.open("w", encoding="utf-8", newline="") as reasons_file:
        writer = csv.DictWriter(reasons_file, fieldnames=_REVIEW_REASONS_HEADER)
        writer.writeheader()

        for index, row in enumerate(rows, start=1):
            stats["seen"] += 1
            slug = (row.get("slug") or "").strip()
            if not slug:
                stats["skipped_missing_slug"] += 1
                logger.warning("crop skip row %s: missing slug", index)
                continue

            source = resolve_source_image(
                row, owner_images=owner_images, site_images=site_images
            )
            if source is None:
                stats["skipped_missing_image"] += 1
                writer.writerow(
                    {
                        "slug": slug,
                        "reason": "missing_image",
                        "source_path": "",
                        "crop_wh": "",
                    }
                )
                stats["review"] += 1
                logger.warning("crop review %s: missing source image", slug)
                continue

            dest_crop = crops_dir / f"{slug}.webp"
            ok, reason, crop_wh = cropper.crop_strict_to_path(
                str(source),
                dest_crop,
                min_side=min_crop_side,
            )
            if ok:
                stats["ok"] += 1
                if progress_every > 0 and stats["ok"] % progress_every == 0:
                    logger.info(
                        "crop progress ok=%s review=%s / seen=%s last=%s",
                        stats["ok"],
                        stats["review"],
                        stats["seen"],
                        slug,
                    )
                continue

            stats["review"] += 1
            reason_key = f"reason_{reason}"
            if reason_key in stats:
                stats[reason_key] += 1
            else:
                stats["reason_other"] += 1

            review_dest = review_dir / f"{slug}{source.suffix.lower() or '.webp'}"
            try:
                shutil.copy2(source, review_dest)
            except OSError as exc:
                logger.warning(
                    "crop review copy failed slug=%s: %s", slug, exc
                )

            wh_str = f"{crop_wh[0]}x{crop_wh[1]}" if crop_wh else ""
            writer.writerow(
                {
                    "slug": slug,
                    "reason": reason,
                    "source_path": str(source),
                    "crop_wh": wh_str,
                }
            )
            if progress_every > 0 and stats["review"] % progress_every == 0:
                logger.info(
                    "crop progress ok=%s review=%s / seen=%s last=%s reason=%s",
                    stats["ok"],
                    stats["review"],
                    stats["seen"],
                    slug,
                    reason,
                )

    logger.info("crop pass done: %s reasons=%s", stats, reasons_path)
    return stats


def import_rows(
    session: Session,
    rows: Sequence[Mapping[str, str]],
    *,
    owner_images: Path,
    site_images: Path,
    static_dir: Path,
    site_categories: Mapping[str, str],
    encoder: DinoOnnxEncoder,
    crops_dir: Path | None = None,
    progress_every: int = 50,
) -> dict[str, int]:
    """Upsert ready+additional rows; return counters.

    When ``crops_dir`` is set, embedding is taken only from
    ``crops_dir/{slug}.webp`` (YOLO label crop). Missing crop → skip insert
    (same as missing image). Full bottle still copied to ``static_dir`` for UI.
    """
    repo = WineRepository(session)
    stats = {
        "seen": 0,
        "upserted": 0,
        "skipped_missing_slug_title": 0,
        "skipped_missing_image": 0,
        "skipped_missing_crop": 0,
        "skipped_encode": 0,
        "skipped_other": 0,
    }
    sweetness_cache: dict[str, int] = {}

    for index, row in enumerate(rows, start=1):
        stats["seen"] += 1
        slug = (row.get("slug") or "").strip()
        title = (row.get("title") or "").strip()
        if not slug or not title:
            stats["skipped_missing_slug_title"] += 1
            logger.warning("skip row %s: missing slug/title", index)
            continue

        source = resolve_source_image(
            row, owner_images=owner_images, site_images=site_images
        )
        if source is None:
            stats["skipped_missing_image"] += 1
            logger.warning("skip %s: missing source image", slug)
            continue

        encode_path: Path
        if crops_dir is not None:
            crop_path = crops_dir / f"{slug}.webp"
            if not crop_path.is_file():
                stats["skipped_missing_crop"] += 1
                logger.warning(
                    "skip %s: no OK catalog crop at %s (review quarantine)",
                    slug,
                    crop_path,
                )
                continue
            encode_path = crop_path
        else:
            encode_path = source

        dest_name = f"{slug}.webp"
        dest = static_dir / dest_name
        image_url = f"/static/wines/{dest_name}"
        try:
            copy_catalog_image(source, dest)
        except OSError as exc:
            stats["skipped_other"] += 1
            logger.warning("skip %s: image copy failed: %s", slug, exc)
            continue

        try:
            embedding = encoder.encode_image(str(encode_path))
        except (FileNotFoundError, OSError, RuntimeError) as exc:
            stats["skipped_encode"] += 1
            logger.warning("skip %s: encode failed: %s", slug, exc)
            if dest.is_file():
                dest.unlink()
            continue

        category = get_or_create_category(
            session, _text_or_sentinel(row.get("category"))
        )
        region = get_or_create_region(session, _text_or_sentinel(row.get("region")))

        sweetness_id: int | None = None
        token = match_sweetness_token(site_categories.get(slug))
        if token is not None:
            if token not in sweetness_cache:
                sweetness_cache[token] = get_or_create_sweetness(session, token).id
            sweetness_id = sweetness_cache[token]

        fields: dict[str, Any] = {
            "title": title,
            "category_id": category.id,
            "color": _text_or_sentinel(row.get("color")),
            "region_id": region.id,
            "grape_variety": _text_or_sentinel(row.get("grape_variety")),
            "description": _text_or_sentinel(row.get("description")),
            "manufacturer": _text_or_sentinel(row.get("manufacturer")),
            "public_rating": _parse_optional_float(row.get("public_rating")),
            "product_url": (row.get("product_url") or "").strip() or None,
            "serving_temperature": (row.get("serving_temperature") or "").strip()
            or None,
            "alcohol_pct": _parse_optional_decimal(row.get("alcohol_pct")),
            "dishes": _parse_dishes_cell(row.get("dishes")),
            "sweetness_id": sweetness_id,
            "image_url": image_url,
            "embedding": embedding,
        }
        try:
            repo.upsert_by_slug(slug, fields)
            session.commit()
            stats["upserted"] += 1
        except Exception:
            session.rollback()
            stats["skipped_other"] += 1
            logger.exception("skip %s: upsert failed", slug)
            if dest.is_file():
                dest.unlink()
            continue

        if progress_every > 0 and stats["upserted"] % progress_every == 0:
            logger.info(
                "progress upserted=%s / seen=%s last=%s encode=%s",
                stats["upserted"],
                stats["seen"],
                slug,
                encode_path.name,
            )

    return stats


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import catalog CSVs into Postgres")
    parser.add_argument(
        "--ready",
        type=Path,
        default=_REPO_ROOT / "scripts" / "catalog_prepare" / "wines_ready.csv",
    )
    parser.add_argument(
        "--additional",
        type=Path,
        default=_REPO_ROOT / "scripts" / "catalog_prepare" / "wines_additional.csv",
    )
    parser.add_argument(
        "--owner-images",
        type=Path,
        default=_REPO_ROOT / "data" / "owner_database" / "images",
    )
    parser.add_argument(
        "--site-images",
        type=Path,
        default=_REPO_ROOT / "data" / "site_database" / "images",
    )
    parser.add_argument(
        "--site-json",
        type=Path,
        default=_REPO_ROOT
        / "data"
        / "site_database"
        / "wines_database_enriched.json",
    )
    parser.add_argument(
        "--static-dir",
        type=Path,
        default=_REPO_ROOT / "static" / "wines",
    )
    parser.add_argument("--progress-every", type=int, default=50)
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional max rows (0 = all); useful for smoke imports",
    )
    parser.add_argument(
        "--crop-first",
        action="store_true",
        help="Run YOLO catalog crop pass before import; encode from crops only",
    )
    parser.add_argument(
        "--crops-dir",
        type=Path,
        default=None,
        help="OK crop dir (default: cropper.catalog_crops_dir from YAML)",
    )
    parser.add_argument(
        "--review-dir",
        type=Path,
        default=None,
        help="Review quarantine dir (default: cropper.catalog_crops_review_dir)",
    )
    parser.add_argument(
        "--recreate-wines",
        action="store_true",
        help="DELETE FROM wines before import (keep sweetness/category/region)",
    )
    parser.add_argument(
        "--skip-crop-pass",
        action="store_true",
        help="With --crop-first semantics via --crops-dir only: reuse existing crops",
    )
    return parser


def _paths_from_settings(
    settings: AppSettings,
    *,
    crops_dir: Path | None,
    review_dir: Path | None,
) -> tuple[Path, Path, int]:
    cropper = settings.cropper
    crops = (
        crops_dir
        if crops_dir is not None
        else _resolve_under_root(cropper.catalog_crops_dir)
    )
    review = (
        review_dir
        if review_dir is not None
        else _resolve_under_root(cropper.catalog_crops_review_dir)
    )
    return crops, review, cropper.min_crop_side


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = build_arg_parser().parse_args(list(argv) if argv is not None else None)
    rows = _read_csv_rows([args.ready, args.additional])
    if args.limit and args.limit > 0:
        rows = rows[: args.limit]
    if not rows:
        logger.error("No CSV rows to import")
        return 1

    settings = load_app_settings()
    crops_dir, review_dir, min_crop_side = _paths_from_settings(
        settings, crops_dir=args.crops_dir, review_dir=args.review_dir
    )

    use_crops = args.crop_first or args.crops_dir is not None or args.skip_crop_pass
    if args.crop_first and not args.skip_crop_pass:
        logger.info(
            "Loading YOLO cropper for catalog pass… crops=%s review=%s min_side=%s",
            crops_dir,
            review_dir,
            min_crop_side,
        )
        cropper = create_label_cropper(settings)
        if not isinstance(cropper, OnnxYoloCropper):
            msg = f"expected OnnxYoloCropper, got {type(cropper)}"
            raise TypeError(msg)
        crop_stats = run_catalog_crop_pass(
            rows,
            owner_images=args.owner_images,
            site_images=args.site_images,
            crops_dir=crops_dir,
            review_dir=review_dir,
            cropper=cropper,
            min_crop_side=min_crop_side,
            progress_every=args.progress_every,
        )
        print(json.dumps({"crop": crop_stats}, ensure_ascii=False))
        use_crops = True

    site_categories = _load_site_categories(args.site_json)
    args.static_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Loading DINO encoder…")
    encoder = create_dino_encoder()
    logger.info(
        "Import start rows=%s embedding_dim=%s static=%s crops=%s",
        len(rows),
        encoder.embedding_dim,
        args.static_dir,
        crops_dir if use_crops else None,
    )

    factory = create_session_factory()
    session = factory()
    try:
        if args.recreate_wines:
            wipe_wines(session)
        stats = import_rows(
            session,
            rows,
            owner_images=args.owner_images,
            site_images=args.site_images,
            static_dir=args.static_dir,
            site_categories=site_categories,
            encoder=encoder,
            crops_dir=crops_dir if use_crops else None,
            progress_every=args.progress_every,
        )
    finally:
        session.close()

    logger.info("Import done: %s", stats)
    print(json.dumps(stats, ensure_ascii=False))
    return 0 if stats["upserted"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
