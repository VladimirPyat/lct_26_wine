#!/usr/bin/env python3
"""YOLO-crop Dev query photos like the API does (label box, else full frame).

Writes ``<dev>/queries_crop/<same filename>`` plus ``<dev>/queries_crop.tsv``
(file, status, reason, width, height). Manifests stay valid: filenames unchanged.

Usage:
  uv run python scripts/crop_dev_queries.py
  uv run python scripts/crop_dev_queries.py --dev <embed_train_data>/dev_a
"""

from __future__ import annotations

import argparse
import csv
import logging
import shutil
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SRC = _REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

logger = logging.getLogger("crop_dev_queries")

DEV_ROOT = _REPO / "data" / "train_dataset" / "embed_train_data"
DEFAULT_DEVS = (DEV_ROOT / "dev_a", DEV_ROOT / "dev_b")
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}
FIELDS = ["file", "status", "reason", "width", "height"]


def crop_dev(dev: Path, cropper) -> dict[str, int]:
    src_dir = dev / "queries"
    out_dir = dev / "queries_crop"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    counts = {"crop": 0, "fallback": 0}
    for src in sorted(p for p in src_dir.iterdir() if p.suffix.lower() in IMG_EXT):
        dest = out_dir / src.name
        # API query path has no min-side gate (only catalog import rejects small).
        ok, reason, wh = cropper.crop_strict_to_path(str(src), dest, min_side=1)
        if ok:
            status = "crop"
        else:
            shutil.copy2(src, dest)
            status = "fallback"
            logger.warning("fallback %s reason=%s", src.name, reason)
        counts[status] += 1
        w, h = wh if wh else ("", "")
        rows.append(dict(zip(FIELDS, (src.name, status, reason, w, h), strict=True)))
    with (dev / "queries_crop.tsv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dev", type=Path, nargs="+", default=list(DEFAULT_DEVS))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    from core.config import load_app_settings
    from core.cropper.onnx_yolo import OnnxYoloCropper, create_label_cropper

    cropper = create_label_cropper(load_app_settings())
    if not isinstance(cropper, OnnxYoloCropper):
        raise TypeError(type(cropper))
    for dev in args.dev:
        c = crop_dev(dev, cropper)
        logger.info("%s: crop=%d fallback=%d", dev.name, c["crop"], c["fallback"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
