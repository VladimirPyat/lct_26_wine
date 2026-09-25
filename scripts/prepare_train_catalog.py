#!/usr/bin/env python3
"""Prepare data/train_dataset for embedding fine-tune.

Steps:
  1. catalog/  — copy data/clean/images, drop MD5 duplicates (keep one per hash)
  2. crop/     — YOLO label crops via OnnxYoloCropper.crop_strict_to_path
  3. by_manufact/ — per-winery folders (winery has >2 wines) with symlinks to crops

Usage:
  uv run python scripts/prepare_train_catalog.py
  uv run python scripts/prepare_train_catalog.py --skip-crop   # catalog + by_manufact only
  uv run python scripts/prepare_train_catalog.py --only by_manufact
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import logging
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

logger = logging.getLogger("prepare_train_catalog")

CLEAN_DIR = _REPO_ROOT / "data" / "clean"
CLEAN_IMAGES = CLEAN_DIR / "images"
CLEAN_CSV = CLEAN_DIR / "wines_integrated_clean.csv"
OUT_ROOT = _REPO_ROOT / "data" / "train_dataset"
CATALOG_DIR = OUT_ROOT / "catalog"
CROP_DIR = OUT_ROOT / "crop"
CROP_REVIEW_DIR = OUT_ROOT / "crop_review"
BY_MANUFACT_DIR = OUT_ROOT / "by_manufact"

_UNSAFE = re.compile(r"[/\\:\0<>\"|?*]+")


def _md5_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        while True:
            block = f.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def _safe_dir_name(name: str) -> str:
    cleaned = _UNSAFE.sub("-", name.strip()) or "unknown"
    return cleaned[:180]


def step_catalog(*, force: bool) -> dict[str, int]:
    """Copy clean images → catalog/, keep one file per MD5."""
    if not CLEAN_IMAGES.is_dir():
        raise FileNotFoundError(f"Missing clean images: {CLEAN_IMAGES}")

    if CATALOG_DIR.exists() and force:
        shutil.rmtree(CATALOG_DIR)
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)

    sources = sorted(
        p
        for p in CLEAN_IMAGES.iterdir()
        if p.is_file() and p.suffix.lower() in {".webp", ".jpg", ".jpeg", ".png"}
    )
    by_hash: dict[str, list[Path]] = defaultdict(list)
    for path in sources:
        by_hash[_md5_file(path)].append(path)

    kept = 0
    dropped = 0
    dup_rows: list[dict[str, str]] = []
    for digest, paths in sorted(by_hash.items(), key=lambda x: x[0]):
        paths_sorted = sorted(paths, key=lambda p: p.name)
        winner = paths_sorted[0]
        dest = CATALOG_DIR / winner.name
        if not dest.exists() or force:
            shutil.copy2(winner, dest)
        kept += 1
        for loser in paths_sorted[1:]:
            dropped += 1
            dup_rows.append(
                {
                    "md5": digest,
                    "kept": winner.name,
                    "dropped": loser.name,
                }
            )

    dup_log = OUT_ROOT / "catalog_sha_dropped.csv"
    with dup_log.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["md5", "kept", "dropped"])
        writer.writeheader()
        writer.writerows(dup_rows)

    stats = {
        "sources": len(sources),
        "unique_md5": len(by_hash),
        "kept": kept,
        "dropped": dropped,
    }
    logger.info(
        "catalog: sources=%s unique_md5=%s kept=%s dropped=%s log=%s",
        stats["sources"],
        stats["unique_md5"],
        stats["kept"],
        stats["dropped"],
        dup_log,
    )
    return stats


def step_crop(*, force: bool, progress_every: int = 50) -> dict[str, int]:
    """YOLO-crop catalog/ → crop/; failures → crop_review/ + reasons.csv."""
    from core.config import load_app_settings
    from core.cropper.onnx_yolo import OnnxYoloCropper, create_label_cropper

    if not CATALOG_DIR.is_dir():
        raise FileNotFoundError(f"Run catalog step first: {CATALOG_DIR}")

    if CROP_DIR.exists() and force:
        shutil.rmtree(CROP_DIR)
    if CROP_REVIEW_DIR.exists() and force:
        shutil.rmtree(CROP_REVIEW_DIR)
    CROP_DIR.mkdir(parents=True, exist_ok=True)
    CROP_REVIEW_DIR.mkdir(parents=True, exist_ok=True)

    settings = load_app_settings()
    yolo = Path(settings.yolo_model_path)
    if not yolo.is_absolute():
        yolo = _REPO_ROOT / yolo
        settings = settings.model_copy(update={"yolo_model_path": str(yolo)})
    cropper = create_label_cropper(settings)
    if not isinstance(cropper, OnnxYoloCropper):
        msg = f"expected OnnxYoloCropper, got {type(cropper)}"
        raise TypeError(msg)
    min_side = settings.cropper.min_crop_side

    sources = sorted(
        p
        for p in CATALOG_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in {".webp", ".jpg", ".jpeg", ".png"}
    )
    reasons_path = CROP_REVIEW_DIR / "reasons.csv"
    stats: dict[str, int] = {
        "seen": 0,
        "ok": 0,
        "review": 0,
        "skipped_existing": 0,
        "reason_no_box": 0,
        "reason_empty_crop": 0,
        "reason_too_small": 0,
        "reason_write_fail": 0,
        "reason_read_fail": 0,
        "reason_other": 0,
    }

    with reasons_path.open("w", encoding="utf-8", newline="") as reasons_file:
        writer = csv.DictWriter(
            reasons_file, fieldnames=["file", "reason", "crop_wh"]
        )
        writer.writeheader()
        for path in sources:
            stats["seen"] += 1
            dest = CROP_DIR / f"{path.stem}.webp"
            if dest.exists() and not force:
                stats["skipped_existing"] += 1
                stats["ok"] += 1
                continue

            ok, reason, crop_wh = cropper.crop_strict_to_path(
                str(path), dest, min_side=min_side
            )
            if ok:
                stats["ok"] += 1
                if progress_every and stats["ok"] % progress_every == 0:
                    logger.info(
                        "crop progress ok=%s review=%s / %s last=%s",
                        stats["ok"],
                        stats["review"],
                        stats["seen"],
                        path.name,
                    )
                continue

            stats["review"] += 1
            key = f"reason_{reason}"
            if key in stats:
                stats[key] += 1
            else:
                stats["reason_other"] += 1
            review_dest = CROP_REVIEW_DIR / path.name
            try:
                shutil.copy2(path, review_dest)
            except OSError as exc:
                logger.warning("review copy failed %s: %s", path.name, exc)
            wh = f"{crop_wh[0]}x{crop_wh[1]}" if crop_wh else ""
            writer.writerow({"file": path.name, "reason": reason, "crop_wh": wh})
            logger.warning("crop review %s reason=%s", path.name, reason)

    logger.info("crop done: %s", stats)
    return stats


def _load_file_to_winery() -> dict[str, str]:
    """Map image filename → Винодельня from clean CSV."""
    if not CLEAN_CSV.is_file():
        raise FileNotFoundError(CLEAN_CSV)
    mapping: dict[str, str] = {}
    with CLEAN_CSV.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            winery = (row.get("Винодельня") or "").strip() or "unknown"
            for key in ("Файл в wines_images", "Название фото"):
                name = (row.get(key) or "").strip()
                if name:
                    mapping[name] = winery
            slug = (row.get("Slug") or "").strip()
            if slug:
                mapping[f"{slug}.webp"] = winery
    return mapping


def step_by_manufact(*, force: bool, min_wines: int = 3) -> dict[str, int]:
    """Symlink crops into by_manufact/<winery>/ for wineries with >= min_wines wines."""
    if not CROP_DIR.is_dir():
        raise FileNotFoundError(f"Run crop step first: {CROP_DIR}")

    if BY_MANUFACT_DIR.exists() and force:
        shutil.rmtree(BY_MANUFACT_DIR)
    BY_MANUFACT_DIR.mkdir(parents=True, exist_ok=True)

    file_to_winery = _load_file_to_winery()
    crops = [
        p
        for p in CROP_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in {".webp", ".jpg", ".jpeg", ".png"}
    ]

    # Count wines per winery among available crops (by stem.webp lookup).
    winery_files: dict[str, list[Path]] = defaultdict(list)
    unknown = 0
    for crop in crops:
        # Prefer exact filename match; crop is always {stem}.webp
        winery = file_to_winery.get(crop.name) or file_to_winery.get(
            f"{crop.stem}.webp"
        )
        if winery is None:
            # Fallback: any catalog extension
            winery = None
            for ext in (".webp", ".jpg", ".jpeg", ".png"):
                winery = file_to_winery.get(f"{crop.stem}{ext}")
                if winery:
                    break
        if winery is None:
            unknown += 1
            winery = "unknown"
        winery_files[winery].append(crop)

    counts = {w: len(files) for w, files in winery_files.items()}
    selected = {w: files for w, files in winery_files.items() if len(files) >= min_wines}

    index_rows: list[dict[str, str | int]] = []
    linked = 0
    for winery, files in sorted(selected.items(), key=lambda x: (-len(x[1]), x[0])):
        n = len(files)
        folder = BY_MANUFACT_DIR / f"{n:03d}_{_safe_dir_name(winery)}"
        folder.mkdir(parents=True, exist_ok=True)
        for crop in sorted(files, key=lambda p: p.name):
            link = folder / crop.name
            if link.exists() or link.is_symlink():
                trash = _REPO_ROOT / ".trash" / "by_manufact_links"
                trash.mkdir(parents=True, exist_ok=True)
                dest = trash / f"{folder.name}__{link.name}"
                if dest.exists() or dest.is_symlink():
                    dest = trash / f"{folder.name}__{link.stem}_{link.stat().st_mtime_ns}{link.suffix}"
                shutil.move(str(link), str(dest))
            link.symlink_to(crop.resolve())
            linked += 1
        index_rows.append({"winery": winery, "n_crops": n, "dir": folder.name})

    index_path = OUT_ROOT / "by_manufact_index.csv"
    with index_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["winery", "n_crops", "dir"])
        writer.writeheader()
        writer.writerows(index_rows)

    stats = {
        "crops": len(crops),
        "wineries_total": len(counts),
        "wineries_selected": len(selected),
        "linked": linked,
        "unknown_winery_crops": unknown,
        "min_wines": min_wines,
    }
    logger.info(
        "by_manufact: selected=%s/%s wineries linked=%s unknown=%s index=%s",
        stats["wineries_selected"],
        stats["wineries_total"],
        linked,
        unknown,
        index_path,
    )
    # Log top sizes for quick orientation
    top = Counter(counts).most_common(15)
    logger.info("by_manufact top sizes: %s", top)
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only",
        choices=("catalog", "crop", "by_manufact", "all"),
        default="all",
    )
    parser.add_argument(
        "--skip-crop",
        action="store_true",
        help="Skip YOLO crop (catalog + by_manufact). by_manufact needs crop/.",
    )
    parser.add_argument("--force", action="store_true", help="Rebuild outputs")
    parser.add_argument(
        "--min-wines",
        type=int,
        default=3,
        help="Min crops per winery for by_manufact (default 3 = more than 2)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    OUT_ROOT.mkdir(parents=True, exist_ok=True)

    only = args.only
    do_catalog = only in ("all", "catalog")
    do_crop = only in ("all", "crop") and not args.skip_crop
    do_man = only in ("all", "by_manufact")

    if do_catalog:
        step_catalog(force=args.force)
    if do_crop:
        step_crop(force=args.force)
    if do_man:
        if not CROP_DIR.is_dir() or not any(CROP_DIR.iterdir()):
            logger.error("by_manufact needs non-empty %s — run crop first", CROP_DIR)
            return 1
        step_by_manufact(force=args.force, min_wines=args.min_wines)

    logger.info("done → %s", OUT_ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
