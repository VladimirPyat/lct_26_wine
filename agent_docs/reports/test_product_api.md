# Test report — PROD-API (Product API `/api/v1` + `CatalogProductService`)

**Branch:** `feat/product-api` (worktree `.worktrees/api`) · **Date:** 2026-09-28 · **Verdict:** **TEST_FAIL** — 1 defect (DEF-1, vector analogs contain the winner after a rerank switch); everything else passes, no env-skips.

Spec: `agent_docs/instructions/tester_product_api.md` A–D · Contract: `agent_docs/contracts/product_api.md`.

## Commands

Env for all: `UV_PROJECT_ENVIRONMENT=/work/lct_vine_final/.venv UV_NO_SYNC=1`; server/in-process runs also `CUDA_VISIBLE_DEVICES="" DATABASE_URL=postgresql+psycopg://vine:vine@127.0.0.1:5432/vine`.

| Command | Exit | Result |
|---|---|---|
| `uv run ruff check src/ tests/` | 0 | All checks passed |
| `timeout 1200 uv run pytest tests/ -v -rs` | 1 | **205 collected: 204 passed, 1 failed, 0 skipped** (86 pre-existing + 119 new) |
| `participant_test.sh` set 1 → `:8081/v1/eval/predict` → `data/tmp/test_product_api_set1.jsonl` | 0 | 27/27 slugs = master baseline |
| `participant_test.sh` set 2 → `:8081/v1/eval/predict` → `data/tmp/test_product_api_set2.jsonl` | 0 | 23/25 = baseline; 2 × HTTP 500 (env, see D1) |
| in-process `predict_slug` with in-memory `compute.device=cpu` for set 2 `q-000004`, `q-000020` | 0 | both = baseline |
| `uv run python scripts/eval_ocr_gate.py --margins 0.08 --out-json data/tmp/…` on branch and on `master` checkout | 0 / 0 | JSON byte-identical; `confident` R@1 49/51 |

The only failure: `tests/test_product_api.py::test_search_low_rerank_switch_vector_excludes_winner` (DEF-1).
DB tests ran against Compose Postgres (read-only); live tests ran against a CPU-only `:8081` started for this run and stopped afterwards (port verified free). `:8080` was not touched (not listening during the run; GPU free).

## New test files

| File | Tests | Marker | Scope |
|---|---|---|---|
| `tests/test_product_hints.py` | 29 | — | A: color / grape / manufacturer hints, blend split, vocabulary |
| `tests/test_product_status.py` | 12 | — | A: `classify_confidence` boundaries, threshold validator |
| `tests/test_product_storage.py` | 24 | — | A: retention, cleanup script, photo path safety, feedback JSONL |
| `tests/test_product_service_db.py` | 16 | `db` | B: `find_wines`, dictionaries, analogs + fallback chain |
| `tests/test_product_api.py` | 33 | `db` (flow part) | C: `/api/v1` via TestClient |
| `tests/test_product_api_live.py` | 2 | `e2e` | C: live real runtime (`PRODUCT_API_BASE`, default `:8081`; skip if down) |
| `tests/test_product_decision_log.py` | 3 | — | D: decision log fields via `run_search` (fake runtime) |
| `tests/product_helpers.py` | — | — | tmp_path settings, `SearchResult` fixtures, DB service builder (skip if DB down) |

`tests/conftest.py`: registered marker `db` (no pyproject change). Thresholds in all status tests come from `ConfidenceSettings` built in the test, not `config/product.yaml`.

## A. Unit — PASS (65/65)

- Color: «КРАСНОЕ СУХОЕ» / «КРАСНОГО» → `Красное`; «ROSÉ» / «rose» → `Розовое`; «BLANC» → `Белое`; «ARANCIONE» → `Оранжевое`; no synonym / empty map → `None`.
- Grapes: «CABERNET SAUVIGNON» → `["Каберне Совиньон"]`; «ПИНО» alone → `[]` (no «Пино Гри»/«Пино Нуар»); «МУСКАТ БЕЛЫЙ» → more specific first; label blend → both grapes; `split_grapes` on `,;/+`, «н/д» → `[]`; vocabulary dedups case variants and resolves all spellings.
- Manufacturer: «ВИНОДЕЛЬНЯ», «ШАТО», «УСАДЬБА ВИНО» → `None`; compact «ФАНАГОРИЯ» / «ШАТОТАМАНЬ» → catalog name.
- Status: boundaries exactly at `not_found_min`, `medium_min`, `high_min` are inclusive (≥); equal thresholds allowed; 3 unordered combinations rejected by the validator.
- Storage: >10 days removed, ≤10 days and foreign files kept; `dry_run` and script `--dry-run` delete nothing; script real run removes 2; `--days -1` → exit 2; startup retention in the service constructor works.
- `photo_path` / `result_path`: `../../etc/passwd`, `..`, empty, non-hex, upper-case hex, 31/33 chars, `*`, id + `/../x` → `None`; unknown id → `None`; JSON-only → `None`; symlink escaping the store → `None`.
- Feedback: line keys exactly `{ts, search_id, slug, verdict, status, confidence_level, winner_slug}`, `slug` defaults to the winner, `not_found` → nulls; unknown / invalid id → `SearchNotFoundError` and no file created.

## B. Service with DB — PASS (16/16)

- `find_wines(color="Красное")`: `limit=5` with `total > 5`; whole list rating DESC NULLS LAST (also on the full catalog); offset pages concatenate to the full order.
- `exclude_manufacturer`: `total` drops by exactly that producer's count, no wine of it remains; `exclude_slugs`: −2 and next wine moves up.
- Every dictionary value (all colors, regions, sweetness, grapes, dishes) returns ≥1 wine; unknown color → `([], 0)`; `get_wine` known / unknown.
- `dictionaries()`: all 5 lists non-empty, trimmed, no exact or case/ё duplicates, grapes have no separators, colors ⊆ 4 categories.
- `analogs_for(found)`: `source == "winner_filters"`, `exclude_manufacturer = winner.manufacturer`, winner excluded, whole filtered set (not only the page) has no winner-producer wine.
- Fallback chain: color+impossible grape → `ocr_filters` with `grape=None` (total = all red); impossible color+grape → `vector` = candidates 2..K; no hints → `vector` honoring `limit`; winner filters empty → `vector`. Unknown / traversal id → `SearchNotFoundError`.

## C. API — 34/35 PASS, 1 FAIL (DEF-1)

Stub-backed (`StubProductService`, no DB): empty 400; undecodable 400; >1 MB (test `max_mb`) 413; exactly 1 MB accepted; `text/plain`, `application/octet-stream`, `image/gif`, `application/pdf` → 415; missing `image` field 422; `/wines?limit=0|51|-1|abc`, `offset=-1` → 422; `/wines/{unknown}` 404 `{"detail"}`; `/search/{unknown}` and `/analogs` 404; `/analogs?limit=0` 422; bad `FeedbackIn` 422; no service → 503. Upload temp dir is empty after every rejection.

DB-backed flow (real `CatalogProductService`, only `run_search` replaced by a deterministic pipeline returning real catalog wines with a test-set `score_1`):
- `POST /search` for scores 0.9 / 0.8 / 0.7 / 0.6 / 0.4 → `found/high`, `found/high`, `found/medium`, `low/low`, `not_found/low`; body validates as `SearchResult`; candidates ≤5, ranks 1..K, scores desc; `winner=None` only for `not_found`; `analogs=None` only for `found`; log fields carry the same status; photo + JSON stored under the exact id; `GET /search/{id}` equals the POST body.
- low + OCR «КРАСНОЕ СУХОЕ» → `ocr_filters`, winner excluded, all red. JPEG uploaded as `photo.webp` stored as `{id}.jpg`. GIF bytes sent as `image/png` → 400, nothing stored, pipeline not called.
- `/analogs` for found → `winner_filters`, no winner / winner producer. `/feedback` → 204 empty body + one JSONL line with the right fields; unknown id → 404, no extra line. `/wines` `{items,total}` rating desc; `/wines/{slug}`; `/dictionaries` equals the service; empty query params ignored.
- **FAIL** `test_search_low_rerank_switch_vector_excludes_winner` → DEF-1.

Live (real runtime, CPU-only `:8081`): owner_eval set 1 `26ddb066.jpg` → 200, `SearchResult` valid, winner = mapping slug `agora-muskat-chernyj`, status matches `classify_confidence(score_1, server thresholds)` (`found/high`, score_1 0.888), `score_1` = candidate 1 score, GET = POST, analogs exclude winner; live 400/415/404/422 checks pass. Feedback intentionally not posted live (would write into the shared `data/tmp/search_feedback.jsonl`; covered on tmp_path).

## D. Regression — PASS (with env note)

1. owner_eval vs `data/tmp/baseline_master_set{1,2}.jsonl`: set 1 — 27/27 identical, hit@1 26/27 (= master). Set 2 over HTTP — 23/25 identical; `q-000004`, `q-000020` returned HTTP 500: PHOCR recognition requests the CUDA provider on a CPU-only server (`RuntimeError: CUDA Provider not available`, server log) — environmental, same as coder's note. Re-run in-process with OCR on CPU (in-memory `compute.device=cpu`, configs untouched): `agora-yachting-cabernet-sauvignon`, `skalistyy-bereg-veter-v-travah-kaberne-fran-krasnoe-suhoe-13` = baseline. **Net 52/52 identical, hit@1 51/52 unchanged.**
2. `eval_ocr_gate.py --margins 0.08`: branch vs `master` output JSON byte-identical (off 49/51, always 45/51, confident 49/51).
3. Decision log (`data/tmp/eval_decisions.jsonl`, 53 lines appended during this run): all 52 eval lines have `score_1`, `score_2` and no product fields; the product line has `search_id`, `status`, `confidence_level`, `endpoint: "product"`, `score_1`, `score_2`. Automated in `test_product_decision_log.py` (eval line without product fields; `log_fields` merged; missing file / empty catalog → no log line).

## Defects

### DEF-1 — `vector` analogs include the winner when OCR rerank switched it (medium)

- **Where:** `src/core/product/catalog_service.py::_vector_analogs` — `rest = [c for c in candidates if c.rank > 1]`.
- **Repro:** `uv run pytest tests/test_product_api.py -k rerank_switch` — `status=low`, `decision.slug` = candidate rank 2 (rerank switch), OCR lines without hints → `analogs.source == "vector"`, and `analogs.wines` contains `winner.slug` (e.g. `fanagoriya-100-ottenkov-krasnogo-pino-nuar-krasnoe-suhoe-135`).
- **Expected:** analogs never contain the winner (as `ocr_filters` / `winner_filters` already guarantee via `exclude_slugs=[winner]`); candidate rank 1 (not the winner) is a valid analog.
- **Actual:** winner shown as its own analog; image top-1 dropped. Same path is used by the `winner_filters` → `vector` fallback in `analogs_for`.
- **Contract:** §4.2 says «candidates rank 2..K», written assuming winner = rank 1; the rerank case is not covered → question appended to `agent_docs/reports/BLOCKED.md` («OPEN — PROD-API vector analogs…»). Likely fix (@Coder): exclude `winner_slug` instead of `rank == 1`.
- Rerank fires on small margins, which overlap with `low` status, so this is reachable in production.

## Observations (not defects)

- §4.2 lists manufacturer among OCR hints that enable `ocr_filters`, but manufacturer is not a filter; with only a manufacturer hint the service goes to `vector`. Consistent with «not used as filter»; UI still gets `hints.manufacturer`.
- `/api/v1/wines` does not expose `exclude_slugs` (not in contract §5 either).
- mypy not run (known pre-existing crash with `python_version=3.11` numpy stubs).

## Next step

@Coder: fix DEF-1 after Planner confirms the rule in `BLOCKED.md`; re-run `uv run pytest tests/test_product_api.py tests/test_product_service_db.py -v`. Everything else is ready for sign-off.
