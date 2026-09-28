# @Tester — PROD-API

**After:** `READY_FOR_TEST (PROD-API)` · **Branch:** `feat/product-api` · **Contract:** [`../contracts/product_api.md`](../contracts/product_api.md)

## A. Unit (no DB, no models)

`tests/test_product_hints.py`:
- [ ] color synonyms: «КРАСНОЕ СУХОЕ» → `Красное`; «ROSÉ» → `Розовое`; none → `None`.
- [ ] grapes: «CABERNET SAUVIGNON» → «Каберне Совиньон» (alias); «ПИНО» alone does not give «Пино Гри»; blends in dictionary split.
- [ ] manufacturer compact match vs stopwords («ВИНОДЕЛЬНЯ» alone → none).

`tests/test_product_status.py` (pure function status/level from score_1 + settings):
- [ ] boundaries at `not_found_min`, `medium_min`, `high_min` (inclusive ≥); validator rejects unordered thresholds.

`tests/test_product_storage.py` (tmp_path):
- [ ] retention deletes > N days, keeps newer; `--dry-run` deletes nothing.
- [ ] `query_photo_path("../../etc/passwd")`, non-hex, unknown id → `None`.
- [ ] feedback JSONL line schema; unknown search → `SearchNotFoundError`.

## B. Service with DB (Compose Postgres; mark `@pytest.mark.db`, report env-skips honestly)

- [ ] `find_wines(color=…)` sorted by `public_rating DESC NULLS LAST`; `limit=5` with `total > 5`; `exclude_manufacturer` removes all of that producer; `exclude_slugs`.
- [ ] `dictionaries()` non-empty lists, no duplicates, no empty strings.
- [ ] `analogs_for(found)` → `source == "winner_filters"`, no wine with winner's manufacturer, winner excluded.
- [ ] fallback chain: impossible filters → color only → `vector`.

## C. API (TestClient with real runtime if models + DB available, else service stubbed via `app.state`)

- [ ] `POST /api/v1/search` owner_eval image → 200, `SearchResult` validates, `candidates` ≤5 sorted desc, `status` consistent with thresholds.
- [ ] `GET /api/v1/search/{id}` equals POST body; unknown → 404.
- [ ] empty file 400; > max_mb 413; `text/plain` 415.
- [ ] `/api/v1/wines?limit=0` → 422; `/api/v1/wines/{unknown}` → 404.
- [ ] `POST /api/v1/feedback` → 204 and line in JSONL; unknown id → 404.

## D. Regression

- [ ] owner_eval 1/2 through `/v1/eval/predict` (`participant_test.sh`, port 8081) → same slugs as `master` baseline; hit@1 unchanged (51/52).
- [ ] `uv run python scripts/eval_ocr_gate.py --margins 0.08` unchanged.
- [ ] decision log lines contain `score_1`, `score_2`; product lines contain `search_id`, `status`.

## Commands

```bash
uv run ruff check src/ tests/
uv run pytest tests/ -v
```

Report `agent_docs/reports/test_product_api.md`; append `TEST_PASS` / `TEST_FAIL (PROD-API)` to `agent_docs/progress/stage_3.md`.
