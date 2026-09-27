# Compare DINOv2 Phase1 vs Phase2 — Dev-A (owner_eval set1)

**Date:** 2026-09-26  
**Scope:** local ONNX encode + retrieval on Dev-A (27 queries); cross-check with Colab training logs under `data/train_dataset/embed_train_data/_logs/`.  
**Decision target:** whether to take Phase2 hard-CE as base for margin, or stay on Phase1.

---

## 1. Verdict (short)

| Source | Phase1 R@5 | Phase2 R@5 | Conclusion |
|--------|------------|------------|------------|
| **ONNX local** (`bin/dinov2_wine_phase*.onnx`) | **0.815** (22/27) | **0.815** (22/27) | parity on R@5; MRR slightly worse on P2 |
| **Colab logs** (torch eval during train) | **0.852** (23/27, P1 e8 best) | **0.778** best (P2 e1); last e6 **0.704** | clear P2 regression vs P1 |

**Recommendation for margin stage:** **base = Phase1 (M1).** Do not take Phase2 hard-CE as the starting checkpoint.

Reasoning: both evidence streams agree that Phase2 does **not** improve R@5 over Phase1. Colab logs show an immediate and persistent drop; ONNX shows at best parity with a worse flip balance (6 LOSE / 5 WIN on rank, and one R@5 boundary loss offset by one win).

---

## 2. Prefight

| Check | Result |
|-------|--------|
| `bin/dinov2_wine_phase1.onnx` | 331M, present |
| `bin/dinov2_wine_phase2.onnx` | 331M, present |
| catalog `dataset/catalog/train` | **2006** images |
| Dev-A queries | **27** |
| `dev_a/manifest.tsv` | OK; **0** `gt_missing` vs local catalog |
| `near/near_groups.csv` | absent at root path; copy exists at `near/v1/near_groups.csv` |
| `_logs/` | present (phase1/2 json + retrieval csv) |
| `_models/phase*/best_adapter/training_metadata.json` | **missing** (folder `_models/` only has empty `v1` stub) |

Artifacts:

- JSON: `agent_docs/reports/compare_dino_onnx_dev_a.json`
- Console log: `agent_docs/reports/compare_dino_onnx_dev_a.log`

Command run (no `--near-groups` → `false_far_rate=nan`):

```bash
.venv/bin/python scripts/compare_dino_onnx.py \
  --onnx bin/dinov2_wine_phase1.onnx bin/dinov2_wine_phase2.onnx \
  --catalog data/train_dataset/embed_train_data/dataset/catalog/train \
  --queries data/train_dataset/embed_train_data/dev_a/queries \
  --manifest data/train_dataset/embed_train_data/dev_a/manifest.tsv \
  --topk 5 --batch 16 \
  --out-json agent_docs/reports/compare_dino_onnx_dev_a.json
```

---

## 3. ONNX results (local CPU)

### 3.1 Summary

| Model | n | R@1 | R@5 | MRR | median_rank | mean_gap12 | false_far |
|-------|---|-----|-----|-----|-------------|------------|-----------|
| phase1 | 27 | 0.519 | **0.815** | 0.631 | 1.0 | 0.060 | skipped |
| phase2 | 27 | 0.519 | **0.815** | 0.625 | 1.0 | 0.062 | skipped |

### 3.2 Flips phase1 → phase2 (any rank change)

Script reports: `better=5 worse=6 changed=11`.

**R@5 boundary flips only (what matters for R@5):**

| Query | P1 rank | P2 rank | Effect |
|-------|---------|---------|--------|
| `ee3e3334.jpeg` | 5 | 6 | **LOSE** R@5 |
| `e3f116c0.jpeg` | 6 | 5 | **WIN** R@5 |

Net R@5 unchanged (22/27 both).

**Other LOSE (rank worse, but already in/out of top-5 as before):**

| Query | P1 → P2 | Note |
|-------|---------|------|
| `90020e08.jpeg` | 1 → 2 | still hit@5 |
| `f212df5b.jpeg` | 3 → 4 | still hit@5 |
| `bd78e0f6.jpg` | 2 → 3 | still hit@5 |
| `6bb419b6.jpg` | 28 → 44 | already miss@5 |
| `2039dd8a.jpg` | 226 → 407 | already miss@5 |

**Other WIN:**

| Query | P1 → P2 |
|-------|---------|
| `ef930b69.jpg` | 263 → 193 |
| `170d9123.jpeg` | 2 → 1 |
| `7bf0507b.jpg` | 21 → 20 |
| `9b04cb8d.jpeg` | 4 → 3 |

### 3.3 ONNX interpretation (per instruction table)

| Picture | Applies? |
|---------|----------|
| P1 R@5 ≥ P2, many LOSE | Partially: R@5 equal; more LOSE than WIN on raw flips; one net-neutral R@5 swap |
| P2 slightly better / parity | **Yes — parity** |
| `n` ≪ 27 / many `gt_missing` | No |

→ Instruction: *«всё равно осторожно; margin стартовать с P1»*.

---

## 4. Colab training logs (same Dev-A, torch)

### 4.1 Phase1 curve (`_logs/phase1_log.json`)

| ep | train_loss | val_loss | R@1 | R@5 | MRR | med | best |
|----|------------|----------|-----|-----|-----|-----|------|
| 1 | 0.406 | 0.140 | 0.370 | 0.556 | 0.453 | 5 | * |
| 2 | 0.070 | 0.040 | 0.444 | 0.704 | 0.550 | 3 | * |
| 3 | 0.053 | 0.024 | 0.519 | 0.741 | 0.613 | 1 | * |
| 4 | 0.047 | 0.031 | 0.444 | 0.704 | 0.560 | 2 | |
| 5 | 0.053 | 0.036 | 0.407 | 0.741 | 0.557 | 2 | |
| 6 | 0.040 | 0.034 | 0.519 | 0.778 | 0.646 | 1 | * |
| 7 | 0.046 | 0.032 | 0.407 | 0.815 | 0.579 | 2 | * |
| 8 | 0.043 | 0.036 | 0.481 | **0.852** | 0.632 | 2 | * |

Best checkpoint: **epoch 8**, R@5 = **23/27**.

### 4.2 Phase2 curve (`_logs/phase2_log.json`)

Config (from notebook builder): start from P1 best; `lr = 1e-4 * 0.5`; `HARD_LOSS_W = 0.5`; `TOPK_HARD = 30`; 6 epochs; near-group exclusion only for `kind==cluster`.

| ep | train | hard | hard/train | val | R@1 | R@5 | MRR | med | best |
|----|-------|------|------------|-----|-----|-----|-----|-----|------|
| 1 | 0.0435 | 0.00117 | 0.027 | 0.021 | 0.519 | **0.778** | 0.637 | 1 | * |
| 2 | 0.0369 | 0.00108 | 0.029 | 0.027 | 0.407 | 0.704 | 0.557 | 2 | |
| 3 | 0.0322 | 0.00176 | 0.055 | 0.017 | 0.407 | **0.667** | 0.525 | 3 | |
| 4 | 0.0374 | 0.00087 | 0.023 | 0.029 | 0.444 | 0.667 | 0.542 | 3 | |
| 5 | 0.0347 | 0.00098 | 0.028 | 0.026 | 0.444 | 0.778 | 0.560 | 2 | |
| 6 | 0.0424 | 0.00103 | 0.024 | 0.024 | 0.444 | 0.704 | 0.565 | 2 | |

**When R@5 degraded:**

1. **Immediately at P2 epoch 1:** 0.852 → 0.778 (−2 queries). This is already the **best** Phase2 checkpoint (`is_best` only on e1).
2. Further drop through e2–e4 (floor **0.667** at e3/e4).
3. Partial bounce at e5 (back to 0.778), then e6 ends at 0.704.

Deltas vs P1 best:

- P1 e8 → P2 best (e1): **−0.074** R@5  
- P1 e8 → P2 last (e6): **−0.148** R@5  

Hard loss stays tiny (~0.001) vs main NCE (~0.03–0.04). Numerically hard CE is a small fraction of the loss; that does **not** by itself prove the hard term is harmless (gradients can still reshape neighbors).

### 4.3 Colab per-query flips (P1 e8 vs P2 epochs)

Source: `_logs/phase1_epoch8_retrieval.csv` vs `phase2_epoch*_retrieval.csv`.

**P2 e1 (exported best, if ONNX = best_adapter):**

| | Queries |
|--|---------|
| LOSE R@5 | `35f764ae.jpg` (3→9), `90020e08.jpeg` (3→9) |
| WIN R@5 | *(none)* |

**Queries that were hit@5 at P1 but miss at some P2 epoch:**

| Query | P1 rank | Fail epochs (rank) |
|-------|---------|-------------------|
| `35f764ae.jpg` | 3 | **all e1–e6** (9…21) — never recovers |
| `90020e08.jpeg` | 3 | **all e1–e6** (9…57) — monotonically worse |
| `6bb419b6.jpg` | 2 | e2:15, e4:6 |
| `ee3e3334.jpeg` | 2 | e2/e3/e4/e6 |
| `f212df5b.jpeg` | 2 | e3/e5/e6 |
| `3c11e5b0.jpeg` | 5 | e3:6 |
| `bd78e0f6.jpg` | 1 | e4:10 |
| `9b04cb8d.jpeg` | 4 | e6:6 |

Only clear late WIN: `e3f116c0.jpeg` (P1 rank 6 → P2 e5:4 / e6:2).

---

## 5. ONNX vs Colab consistency (important caveat)

Per-query ranks **do not match** between Colab torch eval and local ONNX, even for Phase1:

| Query | Colab P1 / P2e1 | ONNX P1 / P2 |
|-------|-----------------|--------------|
| `ef930b69.jpg` | 3 / 2 | **263 / 193** |
| `6bb419b6.jpg` | 2 / 2 | **28 / 44** |
| `170d9123.jpeg` | 6 / 6 | **2 / 1** |
| `90020e08.jpeg` | 3 / 9 | **1 / 2** |
| `ee3e3334.jpeg` | 2 / 1 | **5 / 6** |

GT files from both manifests exist in local catalog (`gt_missing=0`). So the gap is likely **eval stack / weights / preprocess**, not missing files:

- torch + notebook preprocess vs ONNXRuntime + `compare_dino_onnx.py` (cv2 resize);
- possible AMP / embedding path differences;
- **unverified** that ONNX was exported exactly from `phase1/best_adapter` e8 and `phase2/best_adapter` e1 (`training_metadata.json` not in the local snapshot).

**What we can still say:** both pipelines agree Phase2 does not beat Phase1 on R@5.  
**What we cannot say:** that ONNX flips are the same queries as Colab LOSE list, or that absolute ONNX ranks equal Colab ranks.

---

## 6. Hypotheses for Phase2 drop (Colab evidence)

Only hypotheses grounded in available artifacts. Confidence labeled. No claim is “proven.”

### H1 — Phase2 training is net harmful on this Dev-A (high confidence on *effect*, not on *mechanism*)

**Evidence:** R@5 falls at P2 e1 and never exceeds P1; best P2 is the first degraded epoch; LOSE≫WIN in retrieval CSVs.  
**Not explained by:** which term (hard CE vs continued InfoNCE vs LR) caused it — logs alone cannot separate.

### H2 — Hard-FAR mining / near-group quality (medium confidence as *plausible*, low as *proven*)

Training excludes same `group_id` only for `kind==cluster`. Singletons are **not** in the near map → their nearest neighbors are always eligible hard FARs.

Examples from P1 tops of Colab LOSE queries (using local `near/v1/near_groups.csv` — **may or may not** be the exact Drive file used in Colab):

| Query | GT group | P1 top1 | Same-group exclusion? |
|-------|----------|---------|------------------------|
| `35f764ae.jpg` | Alma Valley::6 | other Alma Chardonnay **same group** | excluded from hard pool |
| `90020e08.jpeg` | Inkerman::3 | `winemaker-selection.webp` (**singleton**, no cluster group) | **not** excluded → eligible hard FAR |
| `f212df5b.jpeg` | Massandra cluster_00 | other Massandra port **different** group | eligible hard FAR |

So for some failing queries, hard mining **could** push away visually near bottles that clustering did not mark as near. For `35f764ae` the main competitor is *inside* the near group, so hard CE is **not** a direct explanation for that fail.

**Cannot confirm without:** the exact `near_groups.csv` used on Drive, hard-pool dumps, and/or `false_far_rate` from `--near-groups` on the same embeddings.

### H3 — “Too-hard” negatives (weak / not supported by loss scale)

`hard_loss` stays ~0.001 (easy two-way CE). That is **not** the signature of a chronically unsolvable hard objective. Does not rule out *wrong* hard FARs (label noise), only argues against “objectives never get small.”

### H4 — Hard loss weight 0.5 too large (insufficient data)

Weight is fixed at 0.5 in the notebook; no ablation. Absolute hard loss is small, but gradient impact unknown. **Cannot decide from these logs alone.**

### H5 — Continued InfoNCE at half LR alone would also drop R@5 (insufficient data)

No control run (Phase2 without hard term). Train/val NCE stay low while R@5 falls → retrieval metric and batch NCE are poorly aligned on 27 queries, but that does not isolate hard CE.

### H6 — Dev-A too small / noisy for Phase2 selection (honest limitation)

n=27 → ±1 query = ±0.037 R@5. The Colab drop (−2 at e1, −5 at floor) is larger than one flip, so “noise only” is unlikely for the *direction*, but absolute levels and ONNX/Colab gaps mean we should not overfit narrative to single queries.

---

## 7. Decision table (restate)

| Question | Answer |
|----------|--------|
| Take Phase2 as base for margin? | **No** |
| Base checkpoint | **Phase1 / M1** |
| Does ONNX show P2 better? | **No** (R@5 tie; MRR slightly down) |
| Do Colab logs show P2 better? | **No** (clear regression from e1) |
| Can we name the root cause? | **No single cause proven**; H1 effect clear; H2 only partially suggested |

---

## 8. What would strengthen / close gaps (if needed later)

Not blocking the Phase1 decision. Missing or useful next:

1. `_models/phase1|phase2/best_adapter/training_metadata.json` — confirm which epochs were exported to ONNX.  
2. Re-run compare with  
   `--near-groups data/train_dataset/embed_train_data/near/v1/near_groups.csv`  
   for `false_far_rate` (optional; ~same encode cost).  
3. Confirm Drive `near_groups.csv` used in Colab == local `near/v1/` (or drop the exact file into the snapshot).  
4. Optional: dump hard pools for LOSE GTs from a restored adapter (needs torch checkpoint, not only ONNX).  
5. Align preprocess (notebook vs `compare_dino_onnx.py`) if ONNX↔Colab rank parity is required for debugging.

---

## 9. Log pointers

| Artifact | Role |
|----------|------|
| `agent_docs/reports/compare_dino_onnx_dev_a.log` | ONNX run stdout |
| `agent_docs/reports/compare_dino_onnx_dev_a.json` | machine-readable summary + flips |
| `_logs/phase1_log.json` / `phase2_log.json` | epoch metrics |
| `_logs/phase1_epoch8_retrieval.csv` | Colab P1 best per-query |
| `_logs/phase2_epoch{1..6}_retrieval.csv` | Colab P2 per-query trajectories |
| `near/v1/near_groups.csv` | local near map (not used in this ONNX run) |
