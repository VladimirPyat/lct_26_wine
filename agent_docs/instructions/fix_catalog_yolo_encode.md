# @BugFixer — Catalog YOLO crop encode + query fallback logging

**Status:** approved by user 2026-09-24 (chat).  
**Reports:** low owner_eval hit@1; analysis in `data/tmp/eval_rank_analysis/`.  
**Related:** `agent_docs/contracts/retrieval.md`, `coder_1_2_catalog_load.md`, `src/db/import_catalog.py`, `src/core/cropper/onnx_yolo.py`, `src/core/retrieve/retriever.py`.

## Problem

1. Catalog import encoded **full** `static/wines/{slug}.webp` with DINO (no YOLO). Query path uses **YOLO → DINO** → domain mismatch, weak cosine / top-K.
2. Full-bottle images must remain in `static/wines/` for UI only; **vector = label crop**.
3. Query already falls back to full frame when no box; fallback is logged at **INFO** — must be louder (**error**/warning) so misses are visible.

## Intended pipeline (SSOT for this fix)

| Path | Image for DINO | Full bottle file |
|------|----------------|------------------|
| Catalog import | YOLO label crop (required for insert) | `static/wines/{slug}.*` for UI only |
| Query / eval | YOLO crop; **fallback = full frame** if no/empty box | N/A |

**Do not** insert a wine embedding from full-frame catalog shot when crop failed or is too small — quarantine for human review instead.

## YOLO box selection (current — keep unless broken)

Already **not** pure argmax conf (`src/core/cropper/onnx_yolo.py` → `select_label_box`):

1. Candidates with `score >= cropper.confidence` (default 0.5).
2. Prefer boxes with frame-area fraction in `[box_area_min, box_area_max]` (0.05–0.50) **and** `conf >= max_conf * box_conf_keep_ratio` (0.85).
3. Among those: maximize `conf * (1 - dist_to_center)`.
4. Else: maximize confidence among all candidates above threshold.
5. No candidates → `None` → fallback behavior (query vs catalog differ — see below).

Document this briefly in manuals if missing. Do **not** change selection heuristics unless a clear bug appears.

## Steps

### A. Config / constants

- Add catalog crop min size (e.g. `min_crop_side: 100` → reject if width **or** height `< 100`). Prefer YAML (`config/compute_cropper.yaml` or import section) — no magic numbers in call sites.
- Paths (under `data/tmp/` unless tooling forbids; create if needed — user approved for this fix):
  - `data/tmp/catalog_crops/` — successful crops (`{slug}.webp` or keep ext)
  - `data/tmp/catalog_crops_review/` — failed / too-small / no-box (copy **source** or failed crop + sidecar reason log)
- Review log file: e.g. `data/tmp/catalog_crops_review/reasons.csv` (`slug`, `reason`, `source_path`, `crop_wh` if any).

### B. Catalog crop pass (before DB rewrite)

1. Read ready + additional CSVs (same as import).
2. For each row: resolve source image → run YOLO cropper on that file (not on already-copied static if paths differ — use import’s image resolution).
3. Outcomes:
   - **OK crop** (≥100×100): write under `catalog_crops/{slug}…`; record for encode.
   - **No box / empty / write fail / too small**: copy original (or failed crop) to `catalog_crops_review/`; append reason; **do not** queue encode list.
4. Print summary counts: ok / review / by reason.

### C. DB reload with crop embeddings

1. Prefer **wipe wines** (hard): `DELETE FROM wines` or truncate; keep `sweetness_levels` seed; categories/regions may stay or rebuild via get-or-create on import.
2. Re-run import path:
   - Still copy/keep **full** bottle → `static/wines/{slug}…` + `image_url` for UI.
   - Embedding = DINO(`catalog_crops/{slug}`) only for OK crops.
   - Rows only in review folder → **skip insert** (log), same as missing image.
3. CLI: extend `scripts/catalog_import.py` / `db.import_catalog` with flags, e.g. `--crop-first`, `--crops-dir`, `--review-dir`, `--recreate-wines`, or a small companion script — document in quickstart.
4. Verify: `COUNT(*)` ≈ number of OK crops; `embedding IS NULL` = 0; spot-check cosine of a known slug (crop query vs crop catalog) is high vs pre-fix baseline.

### D. Query / eval fallback logging

1. Keep fallback to **full image** when no/empty box (`LabelCropper` already returns `used_fallback=True` + original path).
2. Change log level to **error** (or warning + structured decision flag): message must include image path and reason (`no_box` / `empty_crop`).
3. Ensure `emit_decision_log` / retrieve bundle surfaces `used_fallback` (already on bundle — add to decision JSON if missing).
4. Do **not** use full-frame fallback for **catalog** vector insert (see B).

### E. Contracts / docs (required)

- Update `agent_docs/contracts/retrieval.md`: remove “catalog may encode without YOLO”; state catalog vector = YOLO crop; full static = UI; query fallback = full frame + log.
- Touch `manuals/architecture.md`, `configuration_guide.md`, `quickstart.md` (crop dirs, recreate, min side).
- Append progress note to `agent_docs/progress/stage_1.md` or `stage_2.md` (append-only).

### F. Lint / smoke

- `uv run ruff check src/ scripts/`
- Optional short smoke: 1–3 OK crops encode + `search_by_embedding`; do **not** require full owner_eval in this fix (parent may re-run set1 after).
- Write `agent_docs/reports/bug_catalog_yolo_encode.md` (before/after, review counts, commands).

## Out of scope

- Changing YOLO weights / retraining DINO.
- Tuning `margin_min` / fuzzy for hit@1.
- Importing `wines_rejected`.
- Frontend UI for static images.

## Acceptance

- [ ] Successful crops in `data/tmp/catalog_crops/`; failures in `…_review/` with reasons
- [ ] `static/wines/` still full-bottle for UI
- [ ] DB embeddings come **only** from OK crops; review-only slugs not inserted (or documented skip)
- [ ] Wines table rebuilt; null embeddings = 0 for imported set
- [ ] Query: no-box → full image + **error-level** log (+ decision flag if applicable)
- [ ] `retrieval.md` + manuals updated
- [ ] Lint clean on touched Python
- [ ] Report written

## Handoff

Append `READY_FOR_TEST` or `FIXED` to progress. Parent may re-run owner_eval set1 for hit@1 delta.
