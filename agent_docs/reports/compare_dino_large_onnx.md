# DINOv2-large Phase1 ONNX — owner_eval summary

Offline ORT + numpy cosine (no DB). Model `bin/dinov2_large_wine_phase1.onnx`.  
Instructions: `agent_docs/drafts/dino_train/COMPARE_dino_large_onnx.md` (paths adapted to `data/owner_eval` + golden).

## Results vs Colab

| Set | Local R@5 | Colab R@5 | Local R@1 | Notes |
|-----|----------:|----------:|----------:|-------|
| owner_eval **1** (Dev-A) | **0.778** (21/27) | 0.889 (24/27) | 0.481 | −3 vs Colab; all Colab misses kept; +3 near-boundary |
| owner_eval **2** (Dev-B) | **0.750** (18/24) | 0.750 (18/24) | 0.583 | R@5 match; 1 miss flip; 1 `gt_missing` |

## With production YOLO query crop (`--crop-queries`)

Queries are full phone frames; catalog and market train are label crops. Cropping queries with
`OnnxYoloCropper` (`bin/yolo_detect_labels_2.onnx`, `config/compute_cropper.yaml`) matches prod.
Crop fallback: 0/27 and 0/25.

| Set | R@5 full frame | R@5 **YOLO crop** | R@1 crop | MRR crop |
|-----|---------------:|------------------:|---------:|---------:|
| owner_eval **1** | 0.778 (21/27) | **0.963** (26/27) | 0.778 | 0.875 |
| owner_eval **2** | 0.750 (18/24) | **0.917** (22/24) | 0.667 | 0.761 |

Colab numbers above were also measured on full frames (same `dev_*/queries`), so they understate the model.

- [miss table with crop](compare_dino_large_onnx_crop_miss_instead_table.md) — 3 misses, 93% of intruder slots are same-house wines
- [set1 crop misses](compare_dino_large_onnx_owner_eval_1_crop_misses.md) · [set2 crop misses](compare_dino_large_onnx_owner_eval_2_crop_misses.md)

## Phase3 vs Phase1 (both with YOLO query crop)

Model `bin/dinov2_large_wine_phase3.onnx`; own catalog cache `compare_dino_large_p3_onnx_catalog_cache.npz`.

| Set | Model | R@1 | R@5 | MRR |
|-----|-------|----:|----:|----:|
| 1 | P1 | 0.778 | 0.963 (26/27) | 0.875 |
| 1 | **P3** | 0.778 | 0.963 (26/27) | 0.874 |
| 2 | P1 | 0.667 | 0.917 (22/24) | 0.761 |
| 2 | **P3** | 0.625 | **0.958** (23/24) | 0.746 |

Rank changes P1 → P3: `750a209e` 8→3 (win @5), `e3f116c0` 8→10, `4ce9195c` 3→4, `4c01cccd` 1→2.

- [P3 miss table](compare_dino_large_p3_onnx_crop_miss_instead_table.md) — 2 misses, all intruders are same-house wines
- [P3 set1 misses](compare_dino_large_p3_onnx_owner_eval_1_crop_misses.md) · [P3 set2 misses](compare_dino_large_p3_onnx_owner_eval_2_crop_misses.md)

## Reports (full frame)

- [set1 / Dev-A](compare_dino_large_onnx_owner_eval_1.md)
- [set2 / Dev-B](compare_dino_large_onnx_owner_eval_2.md)
- **Miss@5 cards + aggregates** (slug → wines CSV):  
  [set1 misses](compare_dino_large_onnx_owner_eval_1_misses.md) ·  
  [set2 misses](compare_dino_large_onnx_owner_eval_2_misses.md)

## Script extras used

`scripts/compare_dino_onnx.py`: `--golden` (jsonl → `{slug}.webp`), `--catalog-cache` (reuse 2006×1024 emb between sets).  
`scripts/report_dino_miss_top5.py`: enrich miss tops via `wines_integrated_updated.csv`.
