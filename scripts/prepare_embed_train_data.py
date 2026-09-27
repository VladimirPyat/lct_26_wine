#!/usr/bin/env python3
"""Build data/train_dataset/embed_train_data/ (Drive-ready layout).

Creates:
  embed_train_data/
    dataset/catalog/{train,val}/   # all crops → train (symlinks); val empty by default
    dataset/market/{train,val}/{anchor,positives}/  # empty stubs (copy from old Drive set)
    dev_a/, dev_b/                 # from owner_eval/1 and /2
    near/                          # drop near_groups.csv later
    phone_2608/                    # resized + YOLO crops from data/26.08.2026
    _models/, _index/, _logs/      # created empty (training fills them)

Index source = dataset/catalog/train (no separate owner_catalog).

Usage:
  uv run python scripts/prepare_embed_train_data.py
  uv run python scripts/prepare_embed_train_data.py --skip-phone
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import shutil
import sys
from pathlib import Path

import cv2

_REPO = Path(__file__).resolve().parents[1]
_SRC = _REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

logger = logging.getLogger("prepare_embed_train_data")

TRAIN_DS = _REPO / "data" / "train_dataset"
CROP_DIR = TRAIN_DS / "crop"
OUT = TRAIN_DS / "embed_train_data"
PHONE_SRC = _REPO / "data" / "26.08.2026"
OWNER_EVAL = _REPO / "data" / "owner_eval"

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}
PHONE_MAX_SIDE = 1600


def _symlink(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        return
    dst.symlink_to(src.resolve())


def _copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        if dst.is_symlink():
            trash = _REPO / ".trash" / "embed_train_data" / "symlink_replaced"
            trash.mkdir(parents=True, exist_ok=True)
            dest = trash / f"{dst.name}_{dst.stat().st_mtime_ns if dst.exists() else 0}"
            shutil.move(str(dst), str(dest))
        elif dst.stat().st_size > 0:
            return
        else:
            trash = _REPO / ".trash" / "embed_train_data" / "empty_replaced"
            trash.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dst), str(trash / dst.name))
    shutil.copy2(src, dst)


def step_dirs() -> None:
    for p in (
        OUT / "dataset" / "catalog" / "train",
        OUT / "dataset" / "catalog" / "val",
        OUT / "dataset" / "market" / "train" / "anchor",
        OUT / "dataset" / "market" / "train" / "positives",
        OUT / "dataset" / "market" / "val" / "anchor",
        OUT / "dataset" / "market" / "val" / "positives",
        OUT / "dev_a" / "queries",
        OUT / "dev_b" / "queries",
        OUT / "near",
        OUT / "phone_2608" / "resized",
        OUT / "phone_2608" / "crops",
        OUT / "phone_2608" / "crop_fail",
        OUT / "_models",
        OUT / "_index",
        OUT / "_logs",
    ):
        p.mkdir(parents=True, exist_ok=True)


def step_catalog_train(*, copy_files: bool = True) -> int:
    """All crop/ → dataset/catalog/train.

    Default: **real file copies** (Drive-safe). Symlinks break when uploading to Google Drive.
    """
    train = OUT / "dataset" / "catalog" / "train"
    n = 0
    for src in sorted(CROP_DIR.iterdir()):
        if not src.is_file() or src.suffix.lower() not in IMG_EXT:
            continue
        dst = train / src.name
        if copy_files:
            _copy_file(src.resolve(), dst)
        else:
            _symlink(src, dst)
        n += 1
    mode = "copies" if copy_files else "symlinks"
    logger.info("catalog/train %s: %s", mode, n)
    return n


def _resolve_catalog_file(slug: str, crop_index: dict[str, Path]) -> Path | None:
    if slug in crop_index:
        return crop_index[slug]
    # prefix / stem startswith
    hits = [p for stem, p in crop_index.items() if stem.startswith(slug) or slug.startswith(stem)]
    if len(hits) == 1:
        return hits[0]
    if hits:
        # shortest stem distance
        hits.sort(key=lambda p: abs(len(p.stem) - len(slug)))
        return hits[0]
    return None


def step_dev(set_id: int, dest_name: str) -> dict:
    """Copy owner_eval/{set}/queries → dev_*/queries + manifest.tsv from golden."""
    src_root = OWNER_EVAL / str(set_id)
    dest = OUT / dest_name
    q_src = src_root / "queries"
    q_dst = dest / "queries"
    if q_dst.exists():
        # replace via trash
        trash = _REPO / ".trash" / "embed_train_data" / f"{dest_name}_queries"
        trash.parent.mkdir(parents=True, exist_ok=True)
        if trash.exists():
            trash = trash.with_name(f"{trash.name}_{trash.stat().st_mtime_ns}")
        shutil.move(str(q_dst), str(trash))
    q_dst.mkdir(parents=True, exist_ok=True)

    crop_index = {
        p.stem: p
        for p in CROP_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in IMG_EXT
    }

    copied = 0
    for src in sorted(q_src.iterdir()):
        if src.is_file() and src.suffix.lower() in IMG_EXT:
            shutil.copy2(src, q_dst / src.name)
            copied += 1

    golden = src_root / "predictions.golden.jsonl"
    rows = []
    missing = []
    for line in golden.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        q_name = Path(rec["image_path"]).name
        slug = rec["predicted_slug"]
        cat = _resolve_catalog_file(slug, crop_index)
        if cat is None:
            missing.append(slug)
            continue
        rows.append({"query_file": q_name, "catalog_file": cat.name, "slug": slug})

    man = dest / "manifest.tsv"
    with man.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["query_file", "catalog_file", "slug"], delimiter="\t")
        w.writeheader()
        w.writerows(rows)

    # also copy queries.tsv for reference
    src_tsv = src_root / "queries.tsv"
    if src_tsv.is_file():
        shutil.copy2(src_tsv, dest / "queries.tsv")

    stats = {"queries": copied, "manifest_rows": len(rows), "missing_gt": len(missing)}
    if missing:
        logger.warning("%s missing catalog for %s: %s", dest_name, missing[:5], len(missing))
    logger.info("%s → %s", dest_name, stats)
    return stats


def _resize_long_side(img_bgr, max_side: int = PHONE_MAX_SIDE):
    h, w = img_bgr.shape[:2]
    m = max(h, w)
    if m <= max_side:
        return img_bgr
    scale = max_side / m
    return cv2.resize(img_bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)


def step_phone(*, max_side: int = PHONE_MAX_SIDE) -> dict:
    """Resize phone JPGs then YOLO-crop labels."""
    from core.config import load_app_settings
    from core.cropper.onnx_yolo import OnnxYoloCropper, create_label_cropper

    if not PHONE_SRC.is_dir():
        logger.warning("phone src missing: %s", PHONE_SRC)
        return {"n": 0}

    settings = load_app_settings()
    yolo = Path(settings.yolo_model_path)
    if not yolo.is_absolute():
        settings = settings.model_copy(update={"yolo_model_path": str(_REPO / yolo)})
    cropper = create_label_cropper(settings)
    if not isinstance(cropper, OnnxYoloCropper):
        raise TypeError(type(cropper))

    resized_dir = OUT / "phone_2608" / "resized"
    crops_dir = OUT / "phone_2608" / "crops"
    fail_dir = OUT / "phone_2608" / "crop_fail"
    reasons = []
    ok = fail = 0

    sources = sorted(
        p for p in PHONE_SRC.iterdir() if p.is_file() and p.suffix.lower() in IMG_EXT
    )
    for src in sources:
        img = cv2.imread(str(src))
        if img is None:
            reasons.append({"file": src.name, "reason": "read_fail"})
            fail += 1
            continue
        small = _resize_long_side(img, max_side)
        rpath = resized_dir / (src.stem + ".jpg")
        cv2.imwrite(str(rpath), small, [int(cv2.IMWRITE_JPEG_QUALITY), 92])

        dest = crops_dir / (src.stem + ".jpg")
        good, reason, wh = cropper.crop_strict_to_path(str(rpath), dest)
        if good:
            ok += 1
            reasons.append({"file": src.name, "reason": "ok", "wh": wh})
        else:
            fail += 1
            # keep resized copy for manual review
            shutil.copy2(rpath, fail_dir / rpath.name)
            reasons.append({"file": src.name, "reason": reason, "wh": wh})
            logger.info("crop fail %s %s", src.name, reason)

    with (OUT / "phone_2608" / "crop_reasons.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file", "reason", "wh"])
        w.writeheader()
        w.writerows(reasons)

    stats = {"sources": len(sources), "ok": ok, "fail": fail}
    logger.info("phone_2608 %s", stats)
    return stats


def write_readme() -> None:
    text = """# embed_train_data (локальная копия структуры Google Drive `2_embed_train_data`)

```
dataset/catalog/train/   — РЕАЛЬНЫЕ копии crop (не symlink — иначе Drive пустой)
dataset/catalog/val/     — пусто ок
dataset/market/...       — из старого 1_embed_train_data
dev_a/, dev_b/           — owner_eval set1 / set2
near/near_groups.csv     — после разметки
_models/, _index/, _logs/— создаёт обучение
```

На Drive заливай **копии** файлов. Symlink с локальной машины на Drive не работают
→ catalog/train будет 0 файлов.

Индекс в ноутбуке = `dataset/catalog/train`.
"""
    (OUT / "README.md").write_text(text, encoding="utf-8")
    (OUT / "dataset" / "market" / "README.md").write_text(
        "Скопируй сюда содержимое market/ из старого `1_embed_train_data/dataset/market`.\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-phone", action="store_true")
    parser.add_argument("--phone-max-side", type=int, default=PHONE_MAX_SIDE)
    parser.add_argument(
        "--symlink-catalog",
        action="store_true",
        help="Use symlinks for catalog/train (NOT for Drive upload)",
    )
    parser.add_argument(
        "--only-catalog",
        action="store_true",
        help="Only (re)materialize catalog/train copies",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if not CROP_DIR.is_dir():
        logger.error("missing crop dir %s", CROP_DIR)
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    step_dirs()
    write_readme()
    step_catalog_train(copy_files=not args.symlink_catalog)
    if args.only_catalog:
        logger.info("only-catalog done → %s", OUT / "dataset" / "catalog" / "train")
        return 0
    step_dev(1, "dev_a")
    step_dev(2, "dev_b")
    if not args.skip_phone:
        step_phone(max_side=args.phone_max_side)
    else:
        logger.info("skip phone")

    logger.info("done → %s", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
