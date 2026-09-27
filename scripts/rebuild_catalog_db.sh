#!/usr/bin/env bash
# Full catalog DB rebuild for an encoder / embedding_dim change (SIG-007 rollout).
#
# Steps:
#   1. prepare import CSV from a cleaned owner-format CSV (data/clean/...)
#   2. alembic upgrade head with VINE_RESET_EMBEDDINGS=1 (wipes wines if dim differs)
#   3. YOLO crop pass + encode + import with --recreate-wines
#
# Destructive (deletes all rows in `wines`): requires --yes.
#
# Usage:
#   scripts/rebuild_catalog_db.sh --yes
#   scripts/rebuild_catalog_db.sh --yes --input data/clean/wines_integrated_cleared.csv \
#       --images-dir data/clean/images -- --encode-batch-size 8 --cropper-device cuda
#   scripts/rebuild_catalog_db.sh --prepare-only   # step 1 only, DB untouched
#
# Args after `--` are passed to scripts/catalog_import.py.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

INPUT="data/clean/wines_integrated_cleared.csv"
IMAGES_DIR="data/clean/images"
READY_CSV="scripts/catalog_prepare/wines_clean_ready.csv"
REJECTED_CSV="scripts/catalog_prepare/wines_clean_rejected.csv"
CONFIRM=0
PREPARE_ONLY=0
IMPORT_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes) CONFIRM=1; shift ;;
    --prepare-only) PREPARE_ONLY=1; shift ;;
    --input) INPUT="$2"; shift 2 ;;
    --images-dir) IMAGES_DIR="$2"; shift 2 ;;
    --ready-csv) READY_CSV="$2"; shift 2 ;;
    --) shift; IMPORT_ARGS=("$@"); break ;;
    -h|--help) sed -n '2,17p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

echo "== 1/3 prepare import CSV from $INPUT"
uv run python scripts/catalog_prepare/prepare_clean_csv.py \
  --input "$INPUT" \
  --images-dir "$IMAGES_DIR" \
  --out-ready "$READY_CSV" \
  --out-rejected "$REJECTED_CSV"

if [[ "$PREPARE_ONLY" -eq 1 ]]; then
  echo "prepare-only: DB untouched"
  exit 0
fi

if [[ "$CONFIRM" -ne 1 ]]; then
  echo "refusing to touch the DB without --yes (wipes and reimports table wines)" >&2
  exit 3
fi

echo "== 2/3 alembic upgrade head (VINE_RESET_EMBEDDINGS=1)"
VINE_RESET_EMBEDDINGS=1 uv run alembic upgrade head

echo "== 3/3 crop + encode + import (--recreate-wines)"
uv run python scripts/catalog_import.py \
  --csv "$READY_CSV" \
  --clean-images "$IMAGES_DIR" \
  --crop-first \
  --recreate-wines \
  "${IMPORT_ARGS[@]}"

echo "done. Check: SELECT count(*), count(embedding) FROM wines;"
