# Strategy: next embed train (after Dev-A top-5 occupants)

**Date:** 2026-09-26  
**Inputs:** `compare_dino_top5_occupants_dev_a.md`, Colab P1/P2 logs, tight-near cleanup in progress.  
**Checkpoint rule:** `phaseK/best_adapter` = best **within** phase K; global pick = compare phase bests at the end.

---

## 1. What the shortlist is made of (Colab P1 e8)

| Slot type vs GT | Share of 135 top-5 slots |
|-----------------|--------------------------:|
| GT | 17% |
| **near_same_group** | **26%** |
| same_winery (not near) | 14% |
| **other** (cross-winery) | **43%** |

P2 e1 barely moves this mix (GT −2 slots, same_winery +3). Hard-CE did **not** clear lookalikes from the shortlist.

### Serial intruders (keep hitting many queries)

Cross / attractor brands (valid hard-FAR / margin targets if not near):

- **MILLSTREAM** `cellar-select-*` (saperavi, blend, cabernet…)
- **AGORA** `agora-saperavi`, `agora-pino-nuar`
- **Chateau de Talu** line (blan / ruzh / roze)
- **Bogovich** cabernet franc / pinot
- **WINEMAFIA** `riesling.webp`
- **Massandra** ports (ONNX especially)

Fine-grained (same line / near) — do **not** treat as hard-FAR:

- Alma Valley chardonnay / shiraz twins  
- Byurne line (`b-yu-rne-*` vs `vinodelnya-byurne-*`)  
- Inkerman `winemaker-selection` vs GT selection (same winery lookalike)

---

## 2. Global model pick (now)

| Phase best | R@5 (Colab Dev-A) | Role |
|------------|-------------------|------|
| **Phase1 best (e8)** | **0.852** | **global winner → M1 base** |
| Phase2 best (e1) | 0.778 | archive / analysis only |

Do not continue from Phase2 weights.

---

## 3. Affirmed next-train recipe (one shot, timebox)

**Name:** Phase 3b — hierarchical margin from M1 (no hard-CE).

| Knob | Value |
|------|--------|
| Start | `phase1/best_adapter` |
| Main loss | InfoNCE (as P1) |
| Extra | hinge margin only, λ ≈ 0.15 |
| Near (tight clusters only) | **mask**: never hard-neg; optional tiny m≈0.03–0.05 vs GT if we want SKU order |
| Same winery, not near | m ≈ 0.10–0.12 |
| Hard pool | top-10 from **frozen M1 index**; exclude tight near; prefer serial intruders above when in top-K |
| Filter | `sim(q,h) < 0.95 * sim(q,g)` (semi-hard / not twin) |
| Refresh pools | every **2** epochs |
| LR | 1e-5 |
| Epochs | 3–4; early stop if R@5 &lt; M1 |
| best_adapter | best **within** this phase; then compare to M1 globally |

### Explicit non-goals this run

- No hard-pair CE / no `hard_w=0.5`  
- No top-30 refresh every epoch  
- No training for deep misses (`2039dd8a` rank~345, `7bf0507b` ~48) — OCR/rerank/crop later  
- No re-expanding loose Par Amour-style clusters into near

### Success criteria (Dev-A Colab-style eval)

1. R@5 ≥ M1 (0.852) — no regression  
2. Ideally +1..2 hits from near-miss class (`e3f116c0` / `170d9123` if crop OK)  
3. Fewer **serial** cross-intruders in top-5 for the LOSE queries (Millstream/Agora) without growing near-collisions

---

## 4. Why this matches the occupant report

- **26% near slots** → problem is fine-grained; pushing near as FAR was the wrong lever (P2 proved it).  
- **43% other** → real room for **selective** far margin on attractors (Millstream, Agora, Talu…), not naive top-30.  
- P1≈P2 mix → need a **different objective** (margin + mask), not “more of the same hard-CE”.

---

## 5. Checklist before Colab

- [ ] Finish tight-only `near/` + regenerate `near_groups.csv`  
- [ ] Optional deny/allow: list of serial intruder stems from this report  
- [ ] Notebook: Phase 3b cell (margin) from M1; `best_adapter` = best of phase  
- [ ] Eval every epoch on Dev-A; one Dev-B check on phase best  
- [ ] Export ONNX only for phase bests; print `training_metadata` epoch/R@5
