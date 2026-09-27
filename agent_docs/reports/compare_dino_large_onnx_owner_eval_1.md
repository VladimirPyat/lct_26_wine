# DINOv2-large Phase1 ONNX — owner_eval set1 (Dev-A)

**Date:** 2026-09-27  
**Model:** `bin/dinov2_large_wine_phase1.onnx` (~1.2G, 1024d, Colab P1 best ep3)  
**Method:** ORT CPU + numpy cosine top-k (no DB / pgvector / API)

---

## Verdict

| Source | n | R@1 | R@5 | MRR |
|--------|--:|----:|----:|----:|
| **ONNX local** | 27 | 0.481 | **0.778** (21/27) | 0.614 |
| **Colab torch** (P1 best ep3) | 27 | 0.481 | **0.889** (24/27) | 0.661 |

Local R@5 is **−3 queries** vs Colab. All three Colab misses remain misses; three extra local misses sit near the R@5 boundary (ranks 7–11). Consistent with draft note: script preprocess = **cv2 square resize**, Colab = **letterbox**.

---

## Setup

| Item | Value |
|------|-------|
| Queries | `data/owner_eval/1/queries` (27) |
| Golden | `data/owner_eval/1/predictions.golden.jsonl` |
| Catalog gallery | `data/train_dataset/embed_train_data/dataset/catalog/train` (**2006**) |
| Top-k | 5 |
| Batch | 8 |
| `gt_missing` | 0 |

```bash
PYTHONUNBUFFERED=1 .venv/bin/python scripts/compare_dino_onnx.py \
  --onnx bin/dinov2_large_wine_phase1.onnx \
  --catalog data/train_dataset/embed_train_data/dataset/catalog/train \
  --queries data/owner_eval/1/queries \
  --golden data/owner_eval/1/predictions.golden.jsonl \
  --topk 5 --batch 8 \
  --catalog-cache agent_docs/reports/compare_dino_large_onnx_catalog_cache.npz \
  --out-json agent_docs/reports/compare_dino_large_onnx_owner_eval_1.json
```

Artifacts:

- [`compare_dino_large_onnx_owner_eval_1.json`](compare_dino_large_onnx_owner_eval_1.json)
- [`compare_dino_large_onnx_owner_eval_1_per_query.json`](compare_dino_large_onnx_owner_eval_1_per_query.json)
- [`compare_dino_large_onnx_owner_eval_1.log`](compare_dino_large_onnx_owner_eval_1.log)
- Catalog emb cache: `compare_dino_large_onnx_catalog_cache.npz` (~7.4M)

---

## Miss @5 (local ONNX)

| Query | Rank | GT slug (stem) | Also Colab miss? |
|-------|-----:|----------------|:----------------:|
| `ef930b69.jpg` | 7 | `vinodelnya-krinitsa-arena-sira-…` | no |
| `8a8ad5d7.jpeg` | 8 | `vinodelnya-byurne-lyublyu-…` | no |
| `3c11e5b0.jpeg` | 11 | `massandra-muskatel-rozovyy-…` | no |
| `7bf0507b.jpg` | 19 | `belbek-belbek-muskat-…` | **yes** |
| `bd78e0f6.jpg` | 34 | `alma-valley-graviti-pino-blan-…` | **yes** |
| `2039dd8a.jpg` | 100 | `alma-valley-alma-graviti-pino-nuar-…` | **yes** |

Colab miss set (`phase1_epochbestA_3_retrieval.csv`): `2039dd8a`, `7bf0507b`, `bd78e0f6` — all three still miss locally.

---

## Notes

- Golden slugs match `dev_a/manifest.tsv` 1:1; queries identical to `embed_train_data/dev_a/queries`.
- Catalog encode ~18 min on this host (CPU ORT, Large); queries then seconds.
