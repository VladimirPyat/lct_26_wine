#!/usr/bin/env bash
# Full catalog rebuild for an encoder / embedding_dim change (SIG-007 rollout).
#
# Steps:
#   1. CSV     — prepare import CSV from the owner CSV (data/owner_database/...)
#   2. assets  — old static/wines + catalog crops → .trash/; YOLO crop pass
#                (crops = DB embeddings) + full bottles → static/wines (UI);
#                verify both are the same image set (verify_catalog_assets.py)
#   3. DB      — alembic upgrade head with VINE_RESET_EMBEDDINGS=1, then encode
#                prepared crops + import with --recreate-wines
#
# Step 3 deletes all rows in `wines`: requires --yes.
#
# Usage:
#   scripts/rebuild_catalog_db.sh --prepare-only            # steps 1-2, DB untouched
#   scripts/rebuild_catalog_db.sh --yes --reuse-assets      # step 3 on prepared assets
#   scripts/rebuild_catalog_db.sh --yes                     # 1-3
#   scripts/rebuild_catalog_db.sh --yes --input data/owner_database/wines_integrated_updated.csv \
#       --images-dir data/owner_database/images -- --encode-batch-size 8
#
# Args after `--` are passed to scripts/catalog_import.py (both import calls).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

INPUT="data/owner_database/wines_integrated_updated.csv"
IMAGES_DIR="data/owner_database/images"
READY_CSV="scripts/catalog_prepare/wines_clean_ready.csv"
REJECTED_CSV="scripts/catalog_prepare/wines_clean_rejected.csv"
STATIC_DIR="static/wines"
CROPS_DIR="data/tmp/catalog_crops"
REVIEW_DIR="data/tmp/catalog_crops_review"
CROPPER_DEVICE="auto"
CONFIRM=0
PREPARE_ONLY=0
REUSE_ASSETS=0
IMPORT_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes) CONFIRM=1; shift ;;
    --prepare-only) PREPARE_ONLY=1; shift ;;
    --reuse-assets) REUSE_ASSETS=1; shift ;;
    --input) INPUT="$2"; shift 2 ;;
    --images-dir) IMAGES_DIR="$2"; shift 2 ;;
    --ready-csv) READY_CSV="$2"; shift 2 ;;
    --cropper-device) CROPPER_DEVICE="$2"; shift 2 ;;
    --) shift; IMPORT_ARGS=("$@"); break ;;
    -h|--help) sed -n '2,21p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ "$PREPARE_ONLY" -eq 0 && "$CONFIRM" -ne 1 ]]; then
  echo "refusing to touch the DB without --yes (wipes and reimports table wines)" >&2
  echo "use --prepare-only to build CSV + crops + static without the DB" >&2
  exit 3
fi

# onnxruntime-gpu needs the pip CUDA 13 / cuDNN libs on the loader path.
NV_LIB="$REPO_ROOT/.venv/lib/python3.12/site-packages/nvidia"
if [[ -d "$NV_LIB/cu13/lib" ]]; then
  export LD_LIBRARY_PATH="$NV_LIB/cu13/lib:$NV_LIB/cudnn/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi

verify_assets() {
  uv run python scripts/catalog_prepare/verify_catalog_assets.py \
    --csv "$READY_CSV" \
    --crops-dir "$CROPS_DIR" \
    --static-dir "$STATIC_DIR" \
    --clean-images "$IMAGES_DIR" \
    --review-csv "$REVIEW_DIR/reasons.csv"
}

if [[ "$REUSE_ASSETS" -eq 0 ]]; then
  echo "== 1/3 prepare import CSV from $INPUT"
  uv run python scripts/catalog_prepare/prepare_clean_csv.py \
    --input "$INPUT" \
    --images-dir "$IMAGES_DIR" \
    --out-ready "$READY_CSV" \
    --out-rejected "$REJECTED_CSV"

  echo "== 2/3 assets: crops (DB) + full bottles (static)"
  TRASH=".trash/catalog_rebuild_$(date +%Y%m%d_%H%M%S)"
  mkdir -p "$TRASH"
  for dir in "$CROPS_DIR" "$REVIEW_DIR"; do
    if [[ -d "$dir" ]]; then mv "$dir" "$TRASH/"; fi
  done
  if compgen -G "$STATIC_DIR/*.webp" > /dev/null; then
    mkdir -p "$TRASH/static_wines"
    find "$STATIC_DIR" -maxdepth 1 -name '*.webp' -exec mv -t "$TRASH/static_wines/" {} +
  fi
  echo "old assets → $TRASH"

  uv run python scripts/catalog_import.py \
    --csv "$READY_CSV" \
    --clean-images "$IMAGES_DIR" \
    --static-dir "$STATIC_DIR" \
    --crops-dir "$CROPS_DIR" \
    --review-dir "$REVIEW_DIR" \
    --crop-first \
    --cropper-device "$CROPPER_DEVICE" \
    --assets-only \
    "${IMPORT_ARGS[@]}"
fi

echo "== verify crops ⇔ static"
verify_assets

if [[ "$PREPARE_ONLY" -eq 1 ]]; then
  echo "prepare-only: DB untouched"
  exit 0
fi

echo "== 3/3 alembic upgrade head (VINE_RESET_EMBEDDINGS=1) + encode + import"
VINE_RESET_EMBEDDINGS=1 uv run alembic upgrade head
uv run python scripts/catalog_import.py \
  --csv "$READY_CSV" \
  --clean-images "$IMAGES_DIR" \
  --static-dir "$STATIC_DIR" \
  --crops-dir "$CROPS_DIR" \
  --skip-crop-pass \
  --recreate-wines \
  "${IMPORT_ARGS[@]}"

echo "done. Check: SELECT count(*), count(embedding) FROM wines;  (≈ ok rows in verify)"
