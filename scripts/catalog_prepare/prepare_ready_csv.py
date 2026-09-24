#!/usr/bin/env python3
"""Build wines_ready / wines_additional / wines_rejected CSVs (+ JSON enrich).

Reads SSOT under ``data/``; writes only under ``scripts/catalog_prepare/``.
See ``agent_docs/contracts/catalog_prepare.md``.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parents[1]
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from image_audit import MIN_SIDE, content_hash, measure_min_side  # noqa: E402

OWNER_CSV = _REPO_ROOT / "data" / "owner_database" / "wines_integrated_updated.csv"
OWNER_IMAGES = _REPO_ROOT / "data" / "owner_database" / "images"
SITE_JSON = _REPO_ROOT / "data" / "site_database" / "wines_database_enriched.json"
SITE_IMAGES = _REPO_ROOT / "data" / "site_database" / "images"

OUT_READY = _SCRIPT_DIR / "wines_ready.csv"
OUT_ADDITIONAL = _SCRIPT_DIR / "wines_additional.csv"
OUT_REJECTED = _SCRIPT_DIR / "wines_rejected.csv"

# Owner CSV column names (Russian headers).
COL_TITLE = "Название вина"
COL_CATEGORY = "Категория"
COL_COLOR = "Цвет"
COL_REGION = "Регион"
COL_GRAPE = "Сорт винограда"
COL_DESCRIPTION = "Описание"
COL_MANUFACTURER = "Винодельня"
COL_SLUG = "Slug"
COL_PHOTO_NAME = "Название фото"
COL_PAGE_URL = "Ссылка на страницу"
COL_OWNER_FILE = "Файл в wines_images"

SHARED_FIELDS = [
    "slug",
    "title",
    "category",
    "color",
    "region",
    "grape_variety",
    "description",
    "manufacturer",
    "source_image",
    "product_url",
    "image_source",
    "public_rating",
    "serving_temperature",
    "alcohol_pct",
    "dishes",
]

_ALCOHOL_NUM = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(?:-|–|—|to)?\s*(\d+(?:[.,]\d+)?)?",
    re.IGNORECASE,
)


def _cell(row: dict[str, str], key: str) -> str:
    return (row.get(key) or "").strip()


def parse_alcohol_pct(raw: object) -> str:
    """Parse JSON alcohol → decimal string or empty (rules from wines_schema)."""
    if raw is None:
        return ""
    text = str(raw).strip()
    if not text:
        return ""
    match = _ALCOHOL_NUM.search(text.replace(",", "."))
    if not match:
        return ""
    try:
        first = Decimal(match.group(1).replace(",", "."))
        second_raw = match.group(2)
        if second_raw:
            second = Decimal(second_raw.replace(",", "."))
            value = max(first, second)
        else:
            value = first
    except InvalidOperation:
        return ""
    if value > 35:
        return ""
    if value != value.to_integral_value():
        quantized = value.quantize(Decimal("0.1"))
    else:
        quantized = value
    return format(quantized, "f")


def _serialize_dishes(raw: object) -> str:
    if raw is None:
        return ""
    if isinstance(raw, list):
        return json.dumps(raw, ensure_ascii=False)
    text = str(raw).strip()
    return text


def _enrich_from_json(
    base: dict[str, str],
    site: dict[str, Any] | None,
) -> dict[str, str]:
    out = dict(base)
    if not site:
        out.setdefault("public_rating", "")
        out.setdefault("serving_temperature", "")
        out.setdefault("alcohol_pct", "")
        out.setdefault("dishes", "")
        return out

    rating = site.get("public_rating")
    if rating is None or rating == "":
        out["public_rating"] = ""
    else:
        out["public_rating"] = str(rating)

    temp = site.get("temperature")
    out["serving_temperature"] = "" if temp is None else str(temp).strip()

    out["alcohol_pct"] = parse_alcohol_pct(site.get("alcohol"))
    out["dishes"] = _serialize_dishes(site.get("dishes"))

    # Fill product_url only if empty (do not overwrite owner text / URL).
    if not out.get("product_url"):
        url = site.get("product_url")
        out["product_url"] = "" if url is None else str(url).strip()
    return out


def _base_row(
    owner: dict[str, str],
    *,
    source_image: str,
    image_source: str,
) -> dict[str, str]:
    return {
        "slug": _cell(owner, COL_SLUG),
        "title": _cell(owner, COL_TITLE),
        "category": _cell(owner, COL_CATEGORY),
        "color": _cell(owner, COL_COLOR),
        "region": _cell(owner, COL_REGION),
        "grape_variety": _cell(owner, COL_GRAPE),
        "description": _cell(owner, COL_DESCRIPTION),
        "manufacturer": _cell(owner, COL_MANUFACTURER),
        "source_image": source_image,
        "product_url": _cell(owner, COL_PAGE_URL),
        "image_source": image_source,
    }


def _load_site_by_slug() -> dict[str, dict[str, Any]]:
    with SITE_JSON.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        msg = f"expected list in {SITE_JSON}"
        raise TypeError(msg)
    by_slug: dict[str, dict[str, Any]] = {}
    for item in payload:
        if not isinstance(item, dict):
            continue
        slug = str(item.get("slug") or "").strip()
        if slug:
            by_slug[slug] = item
    return by_slug


def _write_csv(
    path: Path,
    rows: list[dict[str, str]],
    *,
    extra: list[str] | None = None,
) -> None:
    fields = list(SHARED_FIELDS)
    if extra:
        for name in extra:
            if name not in fields:
                fields.append(name)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def main() -> int:
    if not OWNER_CSV.is_file():
        print(f"ERROR: missing {OWNER_CSV}", file=sys.stderr)
        return 1
    if not SITE_JSON.is_file():
        print(f"ERROR: missing {SITE_JSON}", file=sys.stderr)
        return 1

    # utf-8-sig strips BOM so «Название вина» matches contract headers.
    with OWNER_CSV.open(encoding="utf-8-sig", newline="") as handle:
        owner_rows = list(csv.DictReader(handle))

    site_by_slug = _load_site_by_slug()
    print(
        f"Owner rows={len(owner_rows)} site JSON={len(site_by_slug)} "
        f"MIN_SIDE={MIN_SIDE}"
    )

    # Per-row owner image metrics.
    owner_file_counts = Counter(
        _cell(row, COL_OWNER_FILE) for row in owner_rows if _cell(row, COL_OWNER_FILE)
    )
    photo_name_counts = Counter(
        _cell(row, COL_PHOTO_NAME) for row in owner_rows if _cell(row, COL_PHOTO_NAME)
    )

    meta: list[dict[str, Any]] = []
    for index, row in enumerate(owner_rows):
        slug = _cell(row, COL_SLUG)
        owner_file = _cell(row, COL_OWNER_FILE)
        photo_name = _cell(row, COL_PHOTO_NAME)
        owner_path = OWNER_IMAGES / owner_file if owner_file else None
        min_side = measure_min_side(owner_path) if owner_path is not None else None
        meta.append(
            {
                "index": index,
                "row": row,
                "slug": slug,
                "owner_file": owner_file,
                "photo_name": photo_name,
                "owner_path": owner_path,
                "min_side": min_side,
            }
        )

    ready_indices: set[int] = set()
    ready_rows: list[dict[str, str]] = []

    for item in meta:
        row = item["row"]
        slug = item["slug"]
        owner_file = item["owner_file"]
        photo_name = item["photo_name"]
        min_side = item["min_side"]

        if not slug or not _cell(row, COL_TITLE):
            continue
        if not owner_file or min_side is None:
            continue
        if min_side < MIN_SIDE:
            continue
        if photo_name and photo_name_counts[photo_name] > 1:
            continue
        if owner_file_counts[owner_file] > 1:
            continue

        base = _base_row(row, source_image=owner_file, image_source="owner")
        enriched = _enrich_from_json(base, site_by_slug.get(slug))
        ready_rows.append(enriched)
        ready_indices.add(item["index"])

    ready_slugs = {r["slug"] for r in ready_rows}

    additional_rows: list[dict[str, str]] = []
    additional_indices: set[int] = set()
    used_hashes: set[str] = set()

    for item in meta:
        if item["index"] in ready_indices:
            continue
        row = item["row"]
        slug = item["slug"]
        min_side = item["min_side"]

        if not slug or slug in ready_slugs:
            continue
        if slug not in site_by_slug:
            continue
        # Owner image exists but is below threshold (site rescue).
        if min_side is None or min_side >= MIN_SIDE:
            continue

        site_name = f"{slug}.webp"
        site_path = SITE_IMAGES / site_name
        site_min = measure_min_side(site_path)
        if site_min is None or site_min < MIN_SIDE:
            continue

        digest = content_hash(site_path)
        if digest is None:
            continue
        if digest in used_hashes:
            continue
        used_hashes.add(digest)

        base = _base_row(row, source_image=site_name, image_source="site")
        enriched = _enrich_from_json(base, site_by_slug.get(slug))
        additional_rows.append(enriched)
        additional_indices.add(item["index"])

    rejected_rows: list[dict[str, str]] = []
    for item in meta:
        if item["index"] in ready_indices or item["index"] in additional_indices:
            continue
        row = item["row"]
        slug = item["slug"]
        owner_file = item["owner_file"]
        photo_name = item["photo_name"]
        min_side = item["min_side"]
        reasons: list[str] = []

        if not slug:
            reasons.append("missing_slug")
        if not _cell(row, COL_TITLE):
            reasons.append("missing_title")
        if not owner_file:
            reasons.append("missing_owner_file")
        elif min_side is None:
            reasons.append("owner_image_missing_or_unreadable")
        elif min_side < MIN_SIDE:
            reasons.append(f"owner_min_side_lt_{MIN_SIDE}")
            if slug not in site_by_slug:
                reasons.append("not_in_site_json")
            else:
                site_path = SITE_IMAGES / f"{slug}.webp"
                site_min = measure_min_side(site_path)
                if site_min is None:
                    reasons.append("site_image_missing_or_unreadable")
                elif site_min < MIN_SIDE:
                    reasons.append(f"site_min_side_lt_{MIN_SIDE}")
                else:
                    digest = content_hash(site_path)
                    if digest is not None and digest in used_hashes and slug not in {
                        r["slug"] for r in additional_rows
                    }:
                        reasons.append("duplicate_site_content_hash")
        else:
            # Large enough owner image but not ready → uniqueness / shared photo.
            if photo_name and photo_name_counts[photo_name] > 1:
                reasons.append("shared_photo_name")
            if owner_file and owner_file_counts[owner_file] > 1:
                reasons.append("duplicate_owner_file")
            if not reasons:
                reasons.append("not_selected_ready")

        if not reasons:
            reasons.append("unclassified")

        base = _base_row(
            row,
            source_image=owner_file,
            image_source="owner" if owner_file else "",
        )
        enriched = _enrich_from_json(base, site_by_slug.get(slug) if slug else None)
        enriched["reason"] = ";".join(reasons)
        rejected_rows.append(enriched)

    _write_csv(OUT_READY, ready_rows)
    _write_csv(OUT_ADDITIONAL, additional_rows)
    _write_csv(OUT_REJECTED, rejected_rows, extra=["reason"])

    print(f"ready={len(ready_rows)} → {OUT_READY.name}")
    print(f"additional={len(additional_rows)} → {OUT_ADDITIONAL.name}")
    print(f"rejected={len(rejected_rows)} → {OUT_REJECTED.name}")
    total = len(ready_rows) + len(additional_rows) + len(rejected_rows)
    print(f"checksum rows: {total} (owner={len(owner_rows)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
