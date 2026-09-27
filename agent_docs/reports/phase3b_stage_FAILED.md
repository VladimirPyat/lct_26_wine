# Phase3b (hierarchical margin) — STAGE FAILED

**Status:** **FAILED** (2026-09-26)  
**Global winner (unchanged):** Phase1 best, Dev-A R@5 = **0.8519** (23/27)  
**Do not ship:** `phase2/best_adapter`, `phase3/best_adapter`, or any post-M1 ONNX from these runs  
**Logs analyzed:** `data/train_dataset/embed_train_data/_logs/` (phase1 + phase2 + phase3 Attempt A)

This report is a **handoff pack** for the next agent. Numbers below are taken only from the JSON/CSV logs in that folder (plus plan/notebook paths for context).

---

## 0. One-line verdict

Phase1 InfoNCE alone reached R@5 **0.852**. Phase2 (hard-CE) and Phase3b Attempt A (InfoNCE + hierarchical hinge) both finished **below** that baseline; Phase3b stopped after the first 4-epoch block (`first_block_flat`). Stage closed as **FAILED**. Keep **M1**.

---

## 1. Metric summary (Dev-A, n=27, Colab SSOT)

| Phase | Best epoch | R@1 | R@5 | MRR | med_rank | vs M1 |
|-------|------------|----:|----:|----:|---------:|------|
| **Phase1** | **8** | 0.481 | **0.852** | 0.632 | 2.0 | **winner** |
| Phase2 | 1 (best-of-phase) | 0.519 | 0.778 | 0.637 | 1.0 | −2 hits |
| Phase3b A | 1 (best-of-phase) | 0.444 | 0.815 | 0.583 | 2.0 | −1 hit |

### Phase1 curve (`phase1_log.json`)

| ep | train_loss | R@5 | is_best |
|---:|-----------:|----:|:-------:|
| 1 | 0.406 | 0.556 | ✓ |
| 2 | 0.070 | 0.704 | ✓ |
| 3 | 0.053 | 0.741 | ✓ |
| 4 | 0.047 | 0.704 | |
| 5 | 0.053 | 0.741 | |
| 6 | 0.040 | 0.778 | ✓ |
| 7 | 0.046 | 0.815 | ✓ |
| 8 | 0.043 | **0.852** | ✓ |

Monotone-ish climb to ep8; last `is_best=true`.

### Phase2 curve (`phase2_log.json`)

| ep | train_loss | hard_loss | R@5 |
|---:|-----------:|----------:|----:|
| 1 | 0.044 | 0.00117 | **0.778** |
| 2 | 0.037 | 0.00108 | 0.704 |
| 3 | 0.032 | 0.00176 | 0.667 |
| 4 | 0.037 | 0.00087 | 0.667 |
| 5 | 0.035 | 0.00098 | 0.778 |
| 6 | 0.042 | 0.00103 | 0.704 |

`hard_loss` stayed ~0.001–0.002 (~2–5% of `train_loss`). Never recovered to 0.852.

### Phase3b Attempt A (`phase3_attemptA_log.json`)

Margins locked: `m_near=0.04`, `m_sw=0.11`, `m_far=0.18`, `λ=0.15`. Baseline logged: `0.8519`.

| ep | train_nce | train_hinge | act_near | act_sw | act_far | mean_gap_far | R@5 | beats_baseline |
|---:|----------:|------------:|---------:|-------:|--------:|-------------:|----:|:--------------:|
| 1 | 0.0415 | 0.00395 | 0.148 | 0.0016 | 0.0015 | 0.554 | 0.815 | no |
| 2 | 0.0430 | 0.00455 | 0.161 | 0.0013 | 0.0005 | 0.553 | 0.778 | no |
| 3 | 0.0354 | 0.00431 | 0.136 | 0.0034 | 0.0021 | 0.560 | 0.815 | no |
| 4 | 0.0471 | 0.00393 | 0.134 | 0.0046 | 0.0011 | 0.559 | 0.815 | no |

Stop after ep4: block best R@5=0.815 ≪ baseline. Attempts B/C from the original grid were **not run**.

---

## 2. Per-query evidence (retrieval CSVs)

Files: `phase1_epochbestA_8_retrieval.csv` (= `phase1_epoch8_…`), `phase2_epoch1_…`, `phase3_epoch{1..4}_…`.

### Hits in top-5 vs M1

| Transition | Lost (≥6) | Gained (≤5) | Stay miss | Stay hit |
|------------|----------:|------------:|----------:|---------:|
| M1 → P2 ep1 | 2 | 0 | 4 | 21 |
| M1 → P3 ep1 | 2 | 1 | 3 | 21 |
| M1 → P3 ep4 | 2 | 1 | 3 | 21 |

**Chronic misses on M1 (never fixed by P2/P3):**

| query | M1 rank | P3e1 rank | P3e4 rank |
|-------|--------:|----------:|----------:|
| `2039dd8a.jpg` | 345 | 687 | 615 |
| `7bf0507b.jpg` | 48 | 47 | 47 |
| `e3f116c0.jpeg` / `170d9123.jpeg` | 6 | 6 / 5 | 5 / 6 |

**M1 → P3e1 regressions (leave top-5):**

| query | M1→P3 rank | gt stem | score_gt M1→P3 | score_top1 M1→P3 |
|-------|------------|---------|----------------:|-----------------:|
| `90020e08.jpeg` | 3→9 | inkermanskiy-…-winemakers-selection-saperavi-… | 0.390→0.369 | 0.523→0.541 |
| `ee3e3334.jpeg` | 2→6 | derbent-…-desono-kaberne-… | 0.397→0.363 | 0.416→0.424 |

For both, **GT cosine fell** and **top-1 intruder rose**; shortlist still dominated by lookalikes (`winemaker-selection`, Millstream cellar-select, Bogovich, …) — same families already visible in M1 tops.

**Net R@5 math:** −2 +1 = −1 hit → 22/27 = 0.815 (matches log).

---

## 3. Hypotheses grounded in these logs only

No speculation beyond what the numbers show.

### H1 — Far / same-winery hinge almost inactive (high, log-backed)

From Attempt A JSON:

- `hinge_active_far` ∈ **[0.0005, 0.0021]** (~0.05–0.2% of samples)
- `hinge_active_sw` ∈ **[0.0013, 0.0046]**
- `hinge_active_near` ∈ **[0.13, 0.16]** (only tier with material activity)
- `mean_gap_far` ≈ **0.55** while `m_far=0.18` → for a typical far neg,  
  `relu(sim_far − sim_pos + m_far) = relu(−0.55 + 0.18) = 0`

So the far margin term almost never fires. Residual `train_hinge≈0.004` is mostly **near** (and negligible sw/far).  
Original grid B (`m_far=0.14`) / C (`m_far=0.22`) keep `m_far ≪ 0.55` → same dead-far regime is expected from these numbers (B/C were not executed).

### H2 — Post-M1 updates move a few borderline ranks the wrong way (high, CSV-backed)

Only 1–2 query flips decide R@5 on n=27. P3e1 loses two queries that were already **rank 2–3** on M1, with measured **drop in `score_gt`** and **rise in `score_top1`**. That is sufficient to explain 0.852→0.815 without claiming a global representation collapse.

### H3 — Hard auxiliary terms stayed tiny vs NCE (medium, log-backed)

- P2: `hard_loss / train_loss` ≈ 0.02–0.05 every epoch, yet R@5 fell from the first epoch.  
- P3: `train_hinge / train_nce` ≈ 0.08–0.11, but almost all hinge mass is **near**, not far.  

Data supports: the **intended** hard/far pressure was weak; whatever moved weights enough to hurt R@5 was largely continued NCE + near-hinge, not an active far margin.

### H4 — Deep misses untouched (medium, CSV-backed)

`2039dd8a.jpg` stays rank hundreds (345→687→615). No phase moved it into a useful band. Any method that only reshuffles top-10 hard pools will not be evidenced as fixing this query in these logs.

### H5 — Ceiling / wrong lever (low–medium; only as a reading of outcomes)

Observed fact: **three** training recipes after the same pipeline, only Phase1’s last checkpoint improved R@5; P2 and P3A did not beat M1. That is consistent with “further fine-tune on this recipe family does not help Dev-A,” but the logs **do not prove** a model-capacity ceiling (n=27, one attempt of Phase3b, far hinge never really on). Treat as open until a run with **live far hinge** (`hinge_active_far` materially > ~0.01) is measured.

---

## 4. Ops reminders for the next agent (Colab)

### 4.1 Speed up catalog indexing

Bottleneck is **Drive I/O**, not GPU. In `embed_train_v3.ipynb` §3:

1. Keep `CONFIG["encode_batch_size"] = 128` (fp16 autocast already on).
2. `encode_paths(..., num_workers=8)` — ThreadPool parallel load/preprocess (default OK; can try up to 16).
3. Index cache: `_index/phase{P}/epoch_{E}/catalog.pt` — reuse when `force=False`.
4. Train/eval loops use `force=True` (need fresh R@5) → encode every epoch. If still **>2–3 min/epoch**:
   ```bash
   !cp -r "/content/drive/MyDrive/ЛЦТ26/2_embed_train_data/dataset/catalog/train" /content/catalog_train
   ```
   then point `OWNER_CATALOG` / `CONFIG["owner_catalog"]` to `/content/catalog_train` (see notebook markdown in §3).

Expect ~**35s / ~2006** images on GPU once files are local or batch+ThreadPool is warm.

### 4.2 ONNX export

Legacy export uses `torch.onnx.export(..., dynamo=False)` → needs package **`onnx`**, not `onnxscript`:

```bash
!pip install -q onnx
```

Separate minimal notebook: `agent_docs/drafts/dino_train/export_onnx_colab.ipynb`.  
**Do not** promote phase2/phase3 ONNX over M1 while stage is FAILED. Local refs:

- `bin/dinov2_wine_phase1.onnx` — keep as production candidate from M1  
- `bin/dinov2_wine_phase2.onnx` — archive only  

Train decisions: **Colab retrieval CSV / JSON**, not local ONNX R@5 (preprocess can differ; prior ONNX compare tied at 0.815).

---

## 5. Pointers (notebook / data / docs)

### Notebook & builder

| Path | Role |
|------|------|
| [`agent_docs/drafts/dino_train/embed_train_v3.ipynb`](../drafts/dino_train/embed_train_v3.ipynb) | **Main Colab notebook** (P1 / P2 archive / P3b) |
| [`agent_docs/drafts/dino_train/_build_embed_train_v3.py`](../drafts/dino_train/_build_embed_train_v3.py) | Regenerates the ipynb |
| [`agent_docs/drafts/dino_train/export_onnx_colab.ipynb`](../drafts/dino_train/export_onnx_colab.ipynb) | Drive → ONNX only |

**Drive root (Colab):** `/content/drive/MyDrive/ЛЦТ26/2_embed_train_data/`

### Dataset (local mirror of Drive layout)

| Path | Role |
|------|------|
| [`data/train_dataset/embed_train_data/`](../../data/train_dataset/embed_train_data/) | Full tree (see README) |
| [`data/train_dataset/embed_train_data/README.md`](../../data/train_dataset/embed_train_data/README.md) | Layout notes (real files, not symlinks) |
| `…/dataset/catalog/train/` | Catalog images for index (~2006) |
| `…/dataset/market/` | Market crops / pairs |
| `…/dev_a/`, `…/dev_b/` | Owner eval sets |
| [`…/near/near_groups.csv`](../../data/train_dataset/embed_train_data/near/near_groups.csv) | Near tiers for Phase3 (upload to Drive `near/`) |
| `…/near/margin_tiers.csv`, `margin_tier_report.md` | Built tiers / QA |
| [`…/_logs/`](../../data/train_dataset/embed_train_data/_logs/) | **This stage’s logs** (analyzed here) |
| `…/_models/` | Adapters (on Drive; local may be sparse) |

### Plans / strategy / prior handoff

| Path | Role |
|------|------|
| [`agent_docs/plans/phase3b_margin_train.md`](../plans/phase3b_margin_train.md) | SSOT plan (status → FAILED) |
| [`agent_docs/drafts/dino_train/STRATEGY_PHASE3B_MARGIN.md`](../drafts/dino_train/STRATEGY_PHASE3B_MARGIN.md) | Loss / mining recipe |
| [`agent_docs/drafts/dino_train/HANDOFF_PHASE2_TO_PHASE3.md`](../drafts/dino_train/HANDOFF_PHASE2_TO_PHASE3.md) | Phase2 close → Phase3 direction |
| [`agent_docs/reports/phase3b_attempt_a.md`](phase3b_attempt_a.md) | Attempt A deep-dive (note: early draft said `far=0`; JSON shows ~1e-3 — treat JSON as SSOT) |

### Near / cosine audits (data prep context)

| Path | Role |
|------|------|
| [`agent_docs/reports/near_cluster_cosine_audit_priority.md`](near_cluster_cosine_audit_priority.md) | Priority pairs |
| [`agent_docs/reports/near_cluster_cosine_audit.md`](near_cluster_cosine_audit.md) | Full audit |
| [`agent_docs/reports/near_cluster_cosine_recheck_top35.md`](near_cluster_cosine_recheck_top35.md) | Recheck |
| `scripts/build_margin_tiers.py`, `scripts/scan_near_groups.py` | Rebuild near CSV |
| `scripts/audit_near_cluster_cosine.py` | Cosine audit |

### Dev-A analysis (why Phase3 was designed)

| Path | Role |
|------|------|
| [`agent_docs/reports/compare_dino_top5_occupants_dev_a.md`](compare_dino_top5_occupants_dev_a.md) | Who sits in top-5 |
| [`agent_docs/reports/compare_dino_confusion_dev_a.md`](compare_dino_confusion_dev_a.md) | Confusion types |
| [`agent_docs/reports/compare_dino_onnx_dev_a.md`](compare_dino_onnx_dev_a.md) | Local ONNX P1 vs P2 |
| [`agent_docs/drafts/dino_train/COMPARE_ONNX_DEV_A.md`](../drafts/dino_train/COMPARE_ONNX_DEV_A.md) | How to re-run ONNX compare |

### Requirements / training docs (read-only `docs/`)

| Path | Role |
|------|------|
| `docs/emb_train.md` / `docs/dino_train/emb_train.md` | Embedding train notes |
| `docs/ЛЦТ дообучение2.md` / `docs/dino_train/ЛЦТ дообучение2.md` | Fine-tune writeup |
| `docs/dino_train.ipynb` | Older train notebook (reference; **not** Colab v3) |

---

## 6. Constraints for follow-up work

1. **Winner = Phase1** until a new run **beats 0.852 on Colab Dev-A** with logged metrics.  
2. Do not continue weights from Phase2 or Phase3 Attempt A.  
3. If another margin attempt is approved: start from `phase1/best_adapter`; require ep1 diagnostics `hinge_active_far` and `mean_gap_far` vs `m_far` in the log (Attempt A proves small `m_far` leaves far dead).  
4. Dev-A n=27 → ±1 hit ≈ 0.037 R@5; report raw hit counts.  
5. No package/lockfile changes unless explicitly approved (`tooling.mdc`).  
6. Workspace only: `/work/lct_vine_final`.

---

## 7. Log file checklist (copied under `_logs/`)

```
phase1_log.json
phase1_epoch{1..8}_retrieval.csv
phase1_epochbestA_8_retrieval.csv
phase1_epochbestB_8_retrieval.csv
phase2_log.json
phase2_epoch{1..6}_retrieval.csv
phase3_attemptA_log.json
phase3_epoch{1..4}_retrieval.csv
```
