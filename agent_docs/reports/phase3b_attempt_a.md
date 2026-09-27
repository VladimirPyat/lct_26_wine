# Phase3b Attempt A — report (FAILED)

**Date:** 2026-09-26  
**Run:** Colab, `embed_train_v3`, `ATTEMPT_ID=A`  
**Base:** `phase1/best_adapter` epoch 8, baseline R@5 = **0.8519** (Dev-A n=27)  
**Global winner after this run:** still **Phase1** (do not ship phase3/best)

---

## 1. Metrics (Dev-A)

| Epoch | R@1 | R@5 | MRR | med_rank | vs M1 |
|------:|----:|----:|----:|---------:|------|
| M1 baseline | — | **0.852** | — | — | — |
| 1 | 0.444 | 0.815 | 0.583 | 2.0 | DOWN |
| 2 | 0.444 | 0.778 | 0.582 | 2.0 | DOWN |
| 3 | 0.444 | 0.815 | 0.589 | 2.0 | DOWN |
| 4 | 0.444 | 0.815 | 0.583 | 2.0 | DOWN |

**Stop:** `first_block_flat` after ep4 (block_best=0.815 ≪ baseline).  
**best_of_phase:** ep1 R@5=0.815 (never beat M1).

Compare prior Phase2 best: R@5=0.778 — Attempt A less harmful than P2 hard-CE, but **no gain**.

---

## 2. Loss / hinge diagnostics (critical)

| Epoch | train nce | train hinge | hinge_act **far** (JSON) | gap_far |
|------:|----------:|------------:|-------------------------:|--------:|
| 1 | 0.0415 | 0.00395 | **0.0015** | 0.554 |
| 2 | 0.0430 | 0.00455 | **0.0005** | 0.553 |
| 3 | 0.0354 | 0.00431 | **0.0021** | 0.560 |
| 4 | 0.0471 | 0.00393 | **0.0011** | 0.559 |

Attempt A margins: `m_near=0.04`, `m_sw=0.11`, `m_far=0.18`, `λ=0.15`.  
SSOT: `_logs/phase3_attemptA_log.json` (Colab print may round far≈0).

**Far hinge effectively dead** (`act_far` ~0.05–0.2%; `act_near` ~14–16%; `act_sw` ~0.1–0.5%). With `gap_far ≈ 0.55` and `m_far=0.18`:

```text
hinge = relu(sim_far − sim_pos + m_far) = relu(−0.55 + 0.18) = 0
```

for a typical far neg. Residual hinge (`h≈0.004`) is almost only **near**; effective update ≈ mild continued InfoNCE + near-hinge → slight drift from M1, R@5 stuck ~0.81.

Full stage handoff: [`phase3b_stage_FAILED.md`](phase3b_stage_FAILED.md).

Far pools: 2006/2006 non-empty (topk=10) — mining ran; negatives were simply **already far enough** vs the geometric margin.

---

## 3. Ops notes (not root cause)

- Catalog encode after patch: ~35s / 2006 @ batch 128 — fine for epoch loop.
- ONNX export cell failed: `ModuleNotFoundError: No module named 'onnx'` → fix with `pip install onnx` (not required for train decisions; M1 ONNX already local).
- `GradScaler` / `autocast` FutureWarnings only.

---

## 4. Hypotheses (ranked)

### H1 — Dead far margin (high confidence)

`m_far` ≪ observed `gap_far`. Grid B/C (`m_far=0.14…0.22`) will fail the same way.

**Test:** Attempt D with `m_far ≈ 0.50…0.55` (at/under current gap). Success criterion on **ep1**: `hinge_act far > 0`. If still 0 → stop immediately.

### H2 — Far pool too easy (medium)

Top-10 after excluding near **and** same-winery leaves only easy cross-winery lookalikes already ~0.55 below GT. Need harder candidates:

- keep same-winery out of near but allow some into far with mid margin, or  
- lower semi-hard gate / take higher-sim cross negs, or  
- mine from **query** embedding (aug) not gallery-self.

**Test:** log mean `sim(q,far)` and fraction of pool with `sim_pos − sim_far < m_far` before train step.

### H3 — Near/sw hinge too weak or noisy (medium–low)

Active hinge mass tiny; Dev-A n=27 ⇒ ±1 hit swings R@5 by ~0.037. Drift may be noise + weak sw/near.

**Test:** After far hinge is alive, ablate near vs sw (one offline attempt).

### H4 — Objective mismatch vs R@5 (medium)

InfoNCE + satisfied margins does not push the serial intruders (Millstream/Agora/…) that occupy top-5. Need margin on **shortlist intruders** (report-driven allowlist), not generic catalog top-10.

**Test:** Prefer serial-intruder stems in far pool when present in top-K.

### H5 — Strategy (not knobs) if D fails (fallback)

If live far hinge + harder pool still cannot beat M1 in one block → hierarchical hinge on this miner is the wrong lever; keep M1, pivot (rerank / OCR / different loss), per original tuner budget.

---

## 5. Next run (locked proposal)

| Knob | Attempt D |
|------|-----------|
| Start | `phase1/best_adapter` only (`RESUME=False`) |
| `m_near` | 0.04 |
| `m_sw` | 0.11 |
| `m_far` | **0.52** |
| `λ` | **0.20** |
| Gate | ep1: if `hinge_act far == 0` → **STOP** (do not burn 4 epochs) |
| Success | R@5 ≥ 0.852 within block, ideally +1 hit; far hinge active |

Do **not** promote `phase3/best_adapter` from Attempt A.

### Colab paste (before Phase3 cell, or edit MARGIN_SETS)

```python
ATTEMPT_ID = "D"
RESUME = False
MARGIN_SETS = {
    "A": {"m_near": 0.04, "m_sw": 0.11, "m_far": 0.18, "lam": 0.15},  # done FAILED
    "D": {"m_near": 0.04, "m_sw": 0.11, "m_far": 0.52, "lam": 0.20},
}
```

Export (optional later):

```bash
!pip install -q onnx
```

(`onnxscript` not required for this TorchScript export path; error was missing **`onnx`**.)

---

## 6. Artifacts

- Drive logs: `_logs/phase3_attemptA_log.json`, `phase3_epoch{1..4}_retrieval.csv`
- Drive weights: `_models/phase3/epoch_*`, `best_adapter` (ep1, **worse than M1**)
- Plan SSOT: `agent_docs/plans/phase3b_margin_train.md`
