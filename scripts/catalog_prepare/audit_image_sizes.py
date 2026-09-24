#!/usr/bin/env python3
"""Audit owner (and optional site) catalog image sizes vs MIN_SIDE.

Writes ``image_size_audit.csv`` and prints a threshold summary.
Does not modify SSOT files under ``data/``.
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parents[1]
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from image_audit import MIN_SIDE, measure_size  # noqa: E402

OWNER_IMAGES = _REPO_ROOT / "data" / "owner_database" / "images"
SITE_IMAGES = _REPO_ROOT / "data" / "site_database" / "images"
OUT_CSV = _SCRIPT_DIR / "image_size_audit.csv"


def _audit_dir(label: str, directory: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if not directory.is_dir():
        print(f"WARN: missing directory {directory}", file=sys.stderr)
        return rows
    for path in sorted(directory.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".webp", ".jpg", ".jpeg", ".png"}:
            continue
        size = measure_size(path)
        if size is None:
            rows.append(
                {
                    "source": label,
                    "filename": path.name,
                    "width": "",
                    "height": "",
                    "min_side": "",
                    "ok_min_side": False,
                    "error": "unreadable",
                }
            )
            continue
        width, height = size
        min_side = min(width, height)
        rows.append(
            {
                "source": label,
                "filename": path.name,
                "width": width,
                "height": height,
                "min_side": min_side,
                "ok_min_side": min_side >= MIN_SIDE,
                "error": "",
            }
        )
    return rows


def main() -> int:
    rows = _audit_dir("owner", OWNER_IMAGES) + _audit_dir("site", SITE_IMAGES)
    fieldnames = [
        "source",
        "filename",
        "width",
        "height",
        "min_side",
        "ok_min_side",
        "error",
    ]
    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    by_source: dict[str, Counter[str]] = {}
    for row in rows:
        source = str(row["source"])
        counter = by_source.setdefault(source, Counter())
        if row["error"]:
            counter["error"] += 1
        elif row["ok_min_side"]:
            counter["ok"] += 1
        else:
            counter["small"] += 1

    print(f"MIN_SIDE={MIN_SIDE}")
    print(f"Wrote {OUT_CSV} ({len(rows)} files)")
    for source, counter in sorted(by_source.items()):
        print(
            f"  {source}: ok={counter['ok']} small={counter['small']} "
            f"error={counter['error']} total={sum(counter.values())}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
