#!/usr/bin/env python3
"""Convert a cleaned owner-format catalog CSV into the import CSV schema.

Input: ``data/wines_integrated_updated.csv`` (Russian owner
headers) with images under ``data/owner_database/images/``; an empty image
column falls back to ``{slug}.webp``. Output (import schema,
``image_source=clean`` → resolved against ``--clean-images`` on import):

- ``scripts/catalog_prepare/wines_clean_ready.csv`` — rows with slug, title and image;
- ``scripts/catalog_prepare/wines_clean_rejected.csv`` — the rest, with ``reason``.

Site JSON enriches rating / temperature / alcohol / dishes (same rules as
``prepare_ready_csv.py``). Import afterwards (see ``manuals/quickstart.md``)::

    uv run python scripts/catalog_import.py \\
        --csv scripts/catalog_prepare/wines_clean_ready.csv \\
        --crop-first --recreate-wines
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parents[1]
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from image_audit import measure_min_side  # noqa: E402
from prepare_ready_csv import (  # noqa: E402
    COL_OWNER_FILE,
    COL_SLUG,
    COL_TITLE,
    SITE_JSON,
    _base_row,
    _cell,
    _enrich_from_json,
    _write_csv,
)

IMAGE_SOURCE_CLEAN = "clean"

DEFAULT_INPUT = _REPO_ROOT / "data" / "wines_integrated_updated.csv"
DEFAULT_IMAGES = _REPO_ROOT / "data" / "owner_database" / "images"
DEFAULT_OUT_READY = _SCRIPT_DIR / "wines_clean_ready.csv"
DEFAULT_OUT_REJECTED = _SCRIPT_DIR / "wines_clean_rejected.csv"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--images-dir", type=Path, default=DEFAULT_IMAGES)
    parser.add_argument("--site-json", type=Path, default=SITE_JSON)
    parser.add_argument("--out-ready", type=Path, default=DEFAULT_OUT_READY)
    parser.add_argument("--out-rejected", type=Path, default=DEFAULT_OUT_REJECTED)
    return parser


def load_site_by_slug(path: Path) -> dict[str, dict[str, Any]]:
    """Site JSON list → ``{slug: item}``; missing file → empty (no enrich)."""
    if not path.is_file():
        print(f"warn: site JSON missing, no enrich: {path}")
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        msg = f"expected list in {path}"
        raise TypeError(msg)
    return {
        str(item.get("slug") or "").strip(): item
        for item in payload
        if isinstance(item, dict) and str(item.get("slug") or "").strip()
    }


def resolve_image_file(row: dict[str, str], images_dir: Path) -> str:
    """Имя файла картинки: колонка владельца, иначе ``{slug}.webp`` если файл есть."""
    image_file = _cell(row, COL_OWNER_FILE)
    if image_file:
        return image_file
    slug = _cell(row, COL_SLUG)
    if slug and (images_dir / f"{slug}.webp").is_file():
        return f"{slug}.webp"
    return ""


def classify_row(row: dict[str, str], images_dir: Path) -> list[str]:
    """Return rejection reasons (empty list → row is importable)."""
    reasons: list[str] = []
    if not _cell(row, COL_SLUG):
        reasons.append("missing_slug")
    if not _cell(row, COL_TITLE):
        reasons.append("missing_title")
    image_file = resolve_image_file(row, images_dir)
    if not image_file:
        reasons.append("missing_image_file")
    elif measure_min_side(images_dir / image_file) is None:
        reasons.append("image_missing_or_unreadable")
    return reasons


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if not args.input.is_file():
        print(f"ERROR: missing {args.input}", file=sys.stderr)
        return 1
    if not args.images_dir.is_dir():
        print(f"ERROR: missing images dir {args.images_dir}", file=sys.stderr)
        return 1

    with args.input.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    site_by_slug = load_site_by_slug(args.site_json)

    ready: list[dict[str, str]] = []
    rejected: list[dict[str, str]] = []
    seen_slugs: set[str] = set()
    for row in rows:
        slug = _cell(row, COL_SLUG)
        reasons = classify_row(row, args.images_dir)
        if slug and slug in seen_slugs:
            reasons.append("duplicate_slug")
        base = _base_row(
            row,
            source_image=resolve_image_file(row, args.images_dir),
            image_source=IMAGE_SOURCE_CLEAN,
        )
        enriched = _enrich_from_json(base, site_by_slug.get(slug) if slug else None)
        if reasons:
            enriched["reason"] = ";".join(reasons)
            rejected.append(enriched)
            continue
        seen_slugs.add(slug)
        ready.append(enriched)

    args.out_ready.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(args.out_ready, ready)
    _write_csv(args.out_rejected, rejected, extra=["reason"])
    print(f"input rows={len(rows)} site JSON={len(site_by_slug)}")
    print(f"ready={len(ready)} → {args.out_ready}")
    print(f"rejected={len(rejected)} → {args.out_rejected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
