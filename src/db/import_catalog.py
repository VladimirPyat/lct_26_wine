"""CLI: import prepared ready+additional CSVs into Compose Postgres.

Usage (from repo root)::

    uv run python -m db.import_catalog

Copies images to ``static/wines/``, encodes with DINO, upserts by slug.
Skips rows on missing image / encode failure (logged).
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
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.retrieve.dino_encoder import DinoOnnxEncoder, create_dino_encoder
from db.models import Category, Region, SweetnessLevel
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


def import_rows(
    session: Session,
    rows: Sequence[Mapping[str, str]],
    *,
    owner_images: Path,
    site_images: Path,
    static_dir: Path,
    site_categories: Mapping[str, str],
    encoder: DinoOnnxEncoder,
    progress_every: int = 50,
) -> dict[str, int]:
    """Upsert ready+additional rows; return counters."""
    repo = WineRepository(session)
    stats = {
        "seen": 0,
        "upserted": 0,
        "skipped_missing_slug_title": 0,
        "skipped_missing_image": 0,
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
            embedding = encoder.encode_image(str(dest))
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
                "progress upserted=%s / seen=%s last=%s",
                stats["upserted"],
                stats["seen"],
                slug,
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
    return parser


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

    site_categories = _load_site_categories(args.site_json)
    args.static_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Loading DINO encoder…")
    encoder = create_dino_encoder()
    logger.info(
        "Import start rows=%s embedding_dim=%s static=%s",
        len(rows),
        encoder.embedding_dim,
        args.static_dir,
    )

    factory = create_session_factory()
    session = factory()
    try:
        stats = import_rows(
            session,
            rows,
            owner_images=args.owner_images,
            site_images=args.site_images,
            static_dir=args.static_dir,
            site_categories=site_categories,
            encoder=encoder,
            progress_every=args.progress_every,
        )
    finally:
        session.close()

    logger.info("Import done: %s", stats)
    print(json.dumps(stats, ensure_ascii=False))
    return 0 if stats["upserted"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
