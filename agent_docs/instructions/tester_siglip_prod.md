# @Tester — SIG: SigLIP2 encoder + OCR confident rerank

**After:** @Coder [`coder_siglip_prod.md`](coder_siglip_prod.md) → `READY_FOR_TEST (SIG)`.  
**Branch:** `feat/siglip-prod`.  
**Plan / contracts:** [`../plans/siglip_prod.md`](../plans/siglip_prod.md), [`../contracts/retrieval.md`](../contracts/retrieval.md), [`../contracts/eval_predict.md`](../contracts/eval_predict.md).

## Goal

Unit coverage for the new preprocess / dim guard and for the already-merged confident OCR policy; remove hardcoded DINO
assumptions from tests. Rollout checks (DB reset, reimport, owner_eval via API) only after the user's explicit ✅.

## A. Fix existing tests (no production changes)

- `tests/test_wine_repository.py`, `tests/test_catalog_load.py`: replace literal `768` with `load_database_settings().embedding_dim`.
- `tests/test_compute_opt.py::test_dino_encoder_ctor_rejects_encode_batch_size_below_one`: must not depend on a model file
  that may be absent (use `tmp_path` dummy file + patched `InferenceSession`, or the configured model path if present).
- `DinoPreprocessSettings` fixtures: keep working with new optional keys.

## B. New unit tests — encoder preprocess (`tests/test_encoder_preprocess.py`)

- [ ] letterbox on 100×200 (h×w) RGB → 256×256, content scaled to 128×256 centered, pad rows equal `pad_fill_rgb`.
- [ ] letterbox output equals `scripts/compare_dino_onnx.py` helper output byte-for-byte (same function or same array).
- [ ] `resize_mode` default = `stretch`; stretch output unchanged vs previous behaviour (shape, no pad).
- [ ] validator: `letterbox` without `pad_fill_rgb` → error; values outside 0..255 → error.
- [ ] mean/std 0.5 normalization: pixel 255 → 1.0, 0 → −1.0.
- [ ] dim guard: stub session whose output `pooler_output` shape `[None, 1152]` + config 768 → `RuntimeError`; symbolic dim → no error.

## C. New unit tests — confident rerank (`tests/test_policy_confident.py`)

Use the real `FuzzyReranker` built from `config/ocr_rerank.yaml` (`load_ocr_rerank_settings()`), mock OCR returning fixed lines,
`RankedHit` with `grape_variety`. Cases (names/strings from the Dev set are fine):

- [ ] `always` mode: text leader replaces top-1 (current behaviour kept).
- [ ] `text_agrees`: leader == image top-1 → winner top-1.
- [ ] `weak_text`: only manufacturer in OCR (both candidates same producer) → keep top-1.
- [ ] `strong_text`: `["AGORA", "CABERNET", "SAUVIGNON", "YACHTING"]`, top-1 = Agora Yachting Shiraz, candidate = Agora Yachting
      Cabernet Sauvignon (grape «Каберне Совиньон») → switch.
- [ ] `not_distinguishing`: confirmed grape is present in top-1's `grape_variety` as well → keep.
- [ ] `text_conflict`: both candidates have their own confirmed distinguishing token → keep.
- [ ] `max_img_drop` set and exceeded → keep, reason `img_drop`.
- [ ] margin ≥ `margin_min` → OCR factory not called (existing 2B-01 still green).
- [ ] decision exposes `rerank_reason`, `text_leader`, `evidence`; `emit_decision_log` writes them (tmp log path).

`label_evidence` edge cases:

- [ ] «Пино Гри» needs both tokens: OCR «ПИНО» only → no grape.
- [ ] digits (vintage) never count as brand.
- [ ] producer stopwords («Винодельня», «Estate») alone do not confirm manufacturer.
- [ ] Latin OCR confirms Cyrillic producer (`GOLUBITSKOE` vs «Голубицкое»).

## D. Offline regression (no DB)

```bash
uv run python scripts/eval_ocr_gate.py --margins 0.08
```

Expect for `siglip2_wine_p1_epoch_3`: `confident` 49/51, broken 0 (uses cached OCR `agent_docs/reports/ocr_lines_dev_crops.json`).

## E. Rollout checks — only after user ✅ (SIG-007)

1. `docker compose up -d`; `VINE_RESET_EMBEDDINGS=1 uv run alembic upgrade head` → `atttypmod` of `wines.embedding` = 1152.
2. Without the env var on a non-empty table with other dim → migration refuses (can be shown on a scratch DB only).
3. `uv run python -m db.import_catalog --crop-first --recreate-wines` → null embeddings 0; row count ≈ OK crops.
4. API up; owner_eval set 1 and set 2 via `participant_test.sh` (commands in `tooling.mdc`); `collect_eval_report.py`.
   Expect hit@1 ≥ 48/51 combined, and each miss explained (dup SKU Alma, Endemy color). Compare top-5 with
   `agent_docs/reports/crop_siglip2_wine_p1_epoch_3_dev_{a,b}_per_query.json`.
5. Latency p50/p95 for encode and total from decision log (CPU and/or GPU — state which).

## Commands

```bash
uv run ruff check src/ tests/
uv run pytest tests/ -v
```

DB-backed tests need Compose Postgres with valid `DATABASE_URL` (see `.env.example`); if unavailable, report them as
env-skipped, not as passes.

## Report + progress

`agent_docs/reports/test_siglip_prod.md`: commands + exit codes, covered cases, offline regression table, rollout results (or
«not run — awaiting ✅»). Append `TEST_PASS` / `TEST_FAIL (SIG)` to `agent_docs/progress/stage_2.md`.
