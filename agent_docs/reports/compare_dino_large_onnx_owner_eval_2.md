# DINOv2-large Phase1 ONNX — owner_eval set2 (Dev-B)

**Date:** 2026-09-27  
**Model:** `bin/dinov2_large_wine_phase1.onnx` (~1.2G, 1024d, Colab P1 best ep3)  
**Method:** ORT CPU + numpy cosine top-k (no DB / pgvector / API); catalog embeddings reused from set1 cache

---

## Verdict

| Source | n | R@1 | R@5 | MRR |
|--------|--:|----:|----:|----:|
| **ONNX local** | 24 (+1 `gt_missing`) | 0.583 | **0.750** (18/24) | 0.667 |
| **Colab torch** (P1 bestB ep3) | 24 | — | **0.750** (18/24) | — |

**R@5 matches Colab exactly.** Miss mix differs by one swap (`4ce9195c` local-only vs `2fe84eca` Colab-only).

---

## Setup

| Item | Value |
|------|-------|
| Queries | `data/owner_eval/2/queries` (25 files) |
| Golden | `data/owner_eval/2/predictions.golden.jsonl` (25 rows) |
| Catalog gallery | `dataset/catalog/train` (**2006**) |
| Scored | **24** (`gt_missing=1`) |
| Top-k | 5 |

`a0c040fc.jpg` → golden slug `skalistyy-bereg-veter-v-travah-kaberne-fran-krasnoe-suhoe-13` — **no** matching `{slug}.webp` in train catalog (same exclusion as `dev_b/manifest.tsv`).

```bash
PYTHONUNBUFFERED=1 .venv/bin/python scripts/compare_dino_onnx.py \
  --onnx bin/dinov2_large_wine_phase1.onnx \
  --catalog data/train_dataset/embed_train_data/dataset/catalog/train \
  --queries data/owner_eval/2/queries \
  --golden data/owner_eval/2/predictions.golden.jsonl \
  --topk 5 --batch 8 \
  --catalog-cache agent_docs/reports/compare_dino_large_onnx_catalog_cache.npz \
  --out-json agent_docs/reports/compare_dino_large_onnx_owner_eval_2.json
```

Artifacts:

- [`compare_dino_large_onnx_owner_eval_2.json`](compare_dino_large_onnx_owner_eval_2.json)
- [`compare_dino_large_onnx_owner_eval_2_per_query.json`](compare_dino_large_onnx_owner_eval_2_per_query.json)
- [`compare_dino_large_onnx_owner_eval_2.log`](compare_dino_large_onnx_owner_eval_2.log)

---

## Miss @5 (local ONNX)

| Query | Rank | GT stem | Also Colab miss? |
|-------|-----:|---------|:----------------:|
| `9b891f99.jpg` | 7 | `golubitskoe-rose` | **yes** |
| `1978bd14.jpg` | 8 | `zolotoe-pole-legend-of-crimea-cabernet-…` | **yes** |
| `4ce9195c.jpg` | 10 | `golubitskoe-estate-pino-nuar-rezerv-…` | no (Colab hit) |
| `1f973b82.jpg` | 44 | `vino-suhoe-krasnoe-endemy-saperavi` | **yes** |
| `54aa8496.jpg` | 58 | `golubitskoe-estate-merlo-rezerv-…` | **yes** |
| `750a209e.jpg` | 150 | `derbent-vino-endemy-kaberne-sovinon-…` | **yes** |

Colab-only miss (`phase1_epochbestB_3_retrieval.csv`): `2fe84eca.jpg` (local hit@5).

`gt_missing`: `a0c040fc.jpg` → `skalistyy-bereg-veter-v-travah-…webp` absent from gallery.
