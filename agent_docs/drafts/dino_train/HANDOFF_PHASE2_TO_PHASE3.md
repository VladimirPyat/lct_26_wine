# Handoff: Embed train Phase2 CLOSED → Phase3b (margin)

**Date:** 2026-09-26  
**Workspace:** `/work/lct_vine_final`  
**Chat language with user:** Russian (code/docs EN per project invariants).

---

## Verdict — Phase 2

**FAILED.** Do not continue from Phase2 weights.

| Checkpoint | Colab Dev-A R@5 | Role |
|------------|----------------:|------|
| Phase1 best (epoch 8) | **0.852** (23/27) | **global winner → base for Phase3** |
| Phase2 best (epoch 1) | 0.778 (21/27) | archive only; never recovered above M1 |

ONNX local (`bin/dinov2_wine_phase*.onnx`): R@5 tie 0.815; MD5 **different** (not byte-identical), but shortlist mix ≈ same. Trust **Colab csv** for train decisions; ONNX preprocess ≠ notebook eval.

**Root failure (minimal hypotheses):**

1. **H1 (effect, high):** Phase2 hard-CE + continued NCE harmed R@5 from epoch 1; best-of-phase is still worse than M1.  
2. **H2 (mechanism, medium):** Naive top-30 hard-FAR with incomplete/loose near → false-FAR (e.g. Inkerman ↔ `winemaker-selection` singleton); near twins still ~26% of top-5 slots — hard-FAR did not clear them.  
3. **H3 (not the main story):** `best_adapter` was “best within phase” starting `best_r5=-1` → P2 ep1 always became best even if ≪ M1. Fixed in notebook: still best-within-phase, but metadata logs vs M1 baseline; **global pick is manual after**.

Do **not** retry hard-pair CE / `hard_w=0.5` / top-30 every epoch.

---

## Phase3 direction (affirmed)

See full recipe: [`agent_docs/drafts/dino_train/STRATEGY_PHASE3B_MARGIN.md`](STRATEGY_PHASE3B_MARGIN.md)

Short:

- Start: **`phase1/best_adapter`** (Drive or re-export ONNX from M1 only for local).  
- Loss: InfoNCE + **hierarchical margin** (λ≈0.15), **no** hard-CE.  
- Near: **tight-only** clusters → mask from hard/far; loose (Par Amour-style) → singletons.  
- Far attractors from reports (Millstream, Agora, Talu, …) → margin targets.  
- Frozen M1 index for pools; refresh every **2** epochs; top-10; `sim(h)<0.95·sim(g)`.  
- LR 1e-5, 3–4 epochs, early stop if R@5 < M1.  
- `phaseK/best_adapter` = best **within** phase; compare phase bests globally at end.

---

## Artifacts — notebooks

| Path | Purpose |
|------|---------|
| [`agent_docs/drafts/dino_train/embed_train_v3.ipynb`](embed_train_v3.ipynb) | **Main Colab notebook** (Phase1 archive + Phase2 archive + Phase3b margin). Rebuild via `_build_embed_train_v3.py`. |
| [`agent_docs/drafts/dino_train/_build_embed_train_v3.py`](_build_embed_train_v3.py) | SSOT generator for the ipynb. |
| [`agent_docs/drafts/dino_train/export_onnx_colab.ipynb`](export_onnx_colab.ipynb) | Minimal Drive→ONNX export (CPU, `dynamo=False`). |
| [`agent_docs/drafts/dino_train/STRATEGY_PHASE3B_MARGIN.md`](STRATEGY_PHASE3B_MARGIN.md) | Affirmed Phase3 recipe. |
| [`agent_docs/drafts/dino_train/COMPARE_ONNX_DEV_A.md`](COMPARE_ONNX_DEV_A.md) | How to run local ONNX compare. |

**Colab Drive root:**  
`/content/drive/MyDrive/ЛЦТ26/2_embed_train_data/`  
(`_models/phase1/best_adapter`, `_logs/`, `_index/`, …)

---

## Artifacts — reports (Dev-A analysis)

| Path | Content |
|------|---------|
| [`agent_docs/reports/compare_dino_onnx_dev_a.md`](../../reports/compare_dino_onnx_dev_a.md) | ONNX P1 vs P2 + Colab log cross-check, verdict M1 |
| [`agent_docs/reports/compare_dino_onnx_dev_a.json`](../../reports/compare_dino_onnx_dev_a.json) | Machine summary + flips |
| [`agent_docs/reports/compare_dino_onnx_dev_a_per_query.json`](../../reports/compare_dino_onnx_dev_a_per_query.json) | Per-query tops ONNX |
| [`agent_docs/reports/compare_dino_confusion_dev_a.md`](../../reports/compare_dino_confusion_dev_a.md) | Error types, winery confusion, LOSE detail |
| [`agent_docs/reports/compare_dino_top5_occupants_dev_a.md`](../../reports/compare_dino_top5_occupants_dev_a.md) | **Who occupies top-5** (intruders / near share) — primary for Phase3 design |
| [`agent_docs/reports/compare_dino_top5_occupants_dev_a.json`](../../reports/compare_dino_top5_occupants_dev_a.json) | Same, JSON |

Training curves / per-query Colab:

- `data/train_dataset/embed_train_data/_logs/phase1_log.json`  
- `data/train_dataset/embed_train_data/_logs/phase2_log.json`  
- `data/train_dataset/embed_train_data/_logs/phase1_epoch8_retrieval.csv`  
- `data/train_dataset/embed_train_data/_logs/phase2_epoch{1..6}_retrieval.csv`

---

## Dataset (local)

Root: **`data/train_dataset/embed_train_data/`**

| Path | Role |
|------|------|
| `dataset/catalog/train/` | ~2006 crops = gallery index |
| `dataset/market/{train,val}/…` | market pairs (if present) |
| `dev_a/queries/` + `dev_a/manifest.tsv` | owner_eval set1 (27) |
| `dev_b/queries/` + `dev_b/manifest.tsv` | owner_eval set2 |
| `near/` | **tight-only cleanup in progress**; root `near_groups.csv` may be absent until rescan |
| `near/v1/near_groups.csv` | **old** snapshot (pre tight-only) — do not use for Phase3 without review |
| `_logs/` | Colab training logs (synced) |
| `_models/` | mostly empty locally; weights on Drive / ONNX in `bin/` |

ONNX:

- `bin/dinov2_wine_phase1.onnx` — M1 export  
- `bin/dinov2_wine_phase2.onnx` — P2 best-of-phase export (not for production)

Scripts:

- `scripts/compare_dino_onnx.py` — local ORT compare  
- `scripts/scan_near_groups.py` — rebuild `near_groups.csv` after folder edits  

Docs (read-only TZ notes): `docs/dino_train/ЛЦТ дообучение2.md`, `docs/dino_train/emb_train.md`

---

## Checkpoint / naming convention (for new agent)

```
_models/phase1/best_adapter   # best WITHIN phase1
_models/phase2/best_adapter   # best WITHIN phase2 (may be worse than M1)
# Global: compare R@5 of both; currently winner = phase1
_models/phase3/…              # next stage — create when implementing
```

`load_checkpoint`: must use `PeftModel.from_pretrained(..., is_trainable=True)` + `enable_input_require_grads()`.  
ONNX export: `output_names=["pooler_output"]`, `dynamo=False`.

---

## Suggested first tasks for new window

1. Human finishes near review (10–30 range). Do **not** rename singleton folders.
2. `uv run python scripts/build_margin_tiers.py --scan` → upload `embed_train_data/near/near_groups.csv` to Drive `near/`.
3. Colab: open rebuilt [`embed_train_v3.ipynb`](embed_train_v3.ipynb); `PHASE=3`, `ATTEMPT_ID="A"` from `phase1/best_adapter`.
4. If first block flat → `ATTEMPT_ID="B"` / `"C"` from M1 again.

---

## Prompt stub for new agent

```
CONSTRAINTS: workspace /work/lct_vine_final only; no .env; no rm -rf; .cursor/ read-only.

Read handoff: agent_docs/drafts/dino_train/HANDOFF_PHASE2_TO_PHASE3.md
Phase2 = FAILED. Base = Phase1 best. Implement Phase3b margin per STRATEGY_PHASE3B_MARGIN.md.
Do not revive hard-CE. Wait for tight near_groups.csv if missing.
```
