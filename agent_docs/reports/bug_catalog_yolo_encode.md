# BUG-catalog-yolo-encode — Catalog full-frame vs query YOLO crop

**ID:** BUG-catalog-yolo-encode  
**Class:** DESIGN (cross-module: cropper + catalog import + retrieval contract)  
**Status:** VERIFIED (smoke + lint; owner_eval optional for parent)  
**Opened:** 2026-09-24  
**Closed:** 2026-09-24  
**Instructions:** `agent_docs/instructions/fix_catalog_yolo_encode.md` (user ✅)

## Problem

Catalog import encoded full `static/wines/{slug}.webp` with DINO (no YOLO). Query path uses YOLO → DINO → domain mismatch. Full-bottle files must stay in `static/wines/` for UI; **vector = label crop**. Failed crops → review quarantine (no full-frame catalog embed). Query no-box fallback stays full frame but must log at **ERROR**.

## Classification rationale

Touches `import_catalog`, cropper config, query logging, and `retrieval.md` — DESIGN. Contracts + fix steps approved; BugFixer executed approved instructions to acceptance (smoke + lint).

## Before → After

| Metric | Before | After |
|--------|--------|-------|
| Catalog DINO input | full `static/wines` | YOLO crop in `data/tmp/catalog_crops/` |
| DB wines | 1950 | **1944** (6 `no_box` quarantined) |
| `embedding IS NULL` | 0 | **0** |
| Query no-box log | INFO | **ERROR** (`reason=no_box\|empty_crop`) |
| Decision JSONL | no crop flag | `used_fallback`, `crop_path`, `query_image` |

## Crop / review counts

- **OK crops:** 1944 → `data/tmp/catalog_crops/`
- **Review:** 6 → `data/tmp/catalog_crops_review/` (all `reason=no_box`)
  - magnatum-blanc-de-blancs
  - fanagoriya-rose-kaberne-sovinon-rozovoe-polusuhoe-13
  - fanagoriya-rose-saperavi-rozovoe-polusuhoe-125
  - roze-1
  - rubin-golodrigi
  - fanagoriya-tochka-saperavi-krasnoe-suhoe-14
- Log: `data/tmp/catalog_crops_review/reasons.csv`
- Run log: `data/tmp/catalog_yolo_encode_run.log`

## Commands

```bash
uv run python scripts/catalog_import.py --crop-first --recreate-wines --progress-every 25
uv run ruff check src/ scripts/
# spot-check: encode OK crop → search_by_embedding → self score ≈ 1.0
```

Config (`config/compute_cropper.yaml`): `min_crop_side: 100`, `catalog_crops_dir`, `catalog_crops_review_dir`.

## Code / docs touched

- `src/core/config.py`, `config/compute_cropper.yaml`
- `src/core/cropper/onnx_yolo.py` — ERROR fallback; `crop_strict_to_path` for catalog
- `src/db/import_catalog.py` — crop pass, `--crop-first`, `--recreate-wines`, encode from crops
- `src/api/eval_pipeline.py` — `used_fallback` in decision extra
- `agent_docs/contracts/retrieval.md`
- `manuals/architecture.md`, `configuration_guide.md`, `quickstart.md`
- Progress: `agent_docs/progress/stage_1.md`, `stage_2.md`

## YOLO `select_label_box` (unchanged)

1. Candidates `score >= confidence`
2. Prefer area fraction in `[box_area_min, box_area_max]` and `conf >= max_conf * box_conf_keep_ratio`
3. Among those: max `conf * (1 - dist_to_center)`
4. Else: max confidence
5. None → query full-frame fallback / catalog review

## Acceptance checklist

- [x] Successful crops in `data/tmp/catalog_crops/`; failures in review + reasons
- [x] `static/wines/` still full-bottle for UI
- [x] DB embeddings only from OK crops; review slugs not inserted
- [x] Wines rebuilt; null embeddings = 0
- [x] Query no-box → full image + ERROR log + decision flag
- [x] `retrieval.md` + manuals updated
- [x] Lint clean
- [x] Report written

## Next

Parent may re-run owner_eval set1 for hit@1 delta. Optional @Tester regression if desired.
