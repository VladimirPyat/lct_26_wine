# Test report — PROD-API-FIX1 (analogs by grape + OCR fallback chain)

**Date:** 2026-09-28 · **Branch:** `feat/product-api` · **Code under test:** `2eace1e` · **Instructions:** `agent_docs/instructions/tester_product_api_fix1.md`
**Contracts:** `product_api.md` §4.2 · `ocr_engine.md` «Engine selection»

## Verdict: **TEST_PASS**

No defects found. All 8 tests that encoded the old chain were rewritten to the new contract (IDs kept, suffix `-fix1`); new coverage added for B / C / D.

## Commands

| Command | Exit | Result |
|---|---|---|
| `uv run ruff check src/ tests/` | 0 | All checks passed |
| `timeout 1200 uv run pytest tests/ -v -rs` | 0 | **278 passed, 2 skipped**, 0 failed (was 195 / 8 failed / 2 skipped on handoff) |
| targeted: `test_product_service_db.py` / `test_product_api.py` / `test_product_hints.py` / `test_ocr_selection.py` / `test_policy_decision.py` / `test_ocr_adapter.py` / `test_eval_predict_api.py` | 0 | 22 / 40 / 59 / 21 / 9 / 6 / 4 passed |
| `grep -rn '"vector"' tests/test_product_*.py tests/product_helpers.py` | 1 (no match) | `make_result` placeholder source changed `vector` → `ocr_filters` |
| `scripts/eval_ocr_gate.py --margins 0.08` HEAD vs pre-fix1 `0d8cbdb` src (see §D) | 0 / 0 | JSON **byte-identical** |

Env-skips (2): `test_product_api_live.py:53`, `:101` — live API not reachable at `127.0.0.1:8081` (no server started; optional per instructions). DB (`@pytest.mark.db`) tests all ran against shared Postgres (read-only) — 0 DB skips.

## A. Rewritten tests (old chain → new contract)

| Test | [TEST-ID] | New expectation checked |
|---|---|---|
| `test_product_service_db.py::test_analogs_for_found_winner_filters` | PA-B3-fix1 | `winner_filters`; `filters.color/region is None`; `filters.grape` = dictionary-canonical first grape; `exclude_manufacturer`, `exclude_slugs == [winner]`; hints = winner color + `[grape]`, `ocr_ran False`; full set (`find_wines(ALL)`) — every wine has the grape as a whole element, other manufacturer, winner excluded; first 5 = `find_wines` order |
| `…::test_analogs_ocr_filters_grape_only` (was `…_color_and_grape`) | PA-B4-fix1 | `ocr_filters`, `color None`, `grape == "Шардоне"`, hints preserved; `total` == grape-only count ≥ white-only count (color not constrained) |
| `…::test_analogs_impossible_grape_empty` (was `…_grape_to_color`) | PA-B5-fix1 | `ocr_filters`, `wines == []`, `total == 0`, `filters.grape` = impossible grape; DB spy: exactly one `count_filters`, no retry |
| `…::test_analogs_color_hint_without_grape_empty` (was `…_color_to_vector`) | PA-B5b-fix1 | color hint, no grape → `ocr_filters`, empty, `total 0`, no DB query |
| `…::test_analogs_no_hints_empty` (was `…_no_hints_vector`) | PA-B5c-fix1 | `ocr_filters`, empty, `grape None`, no DB query |
| `…::test_analogs_winner_no_match_or_no_grape_empty` (was `…_winner_fallback_chain`) | PA-B5d-fix1 | (1) real dictionary grape found only at winner's manufacturer → `winner_filters`, empty, one `count_filters`; (2) grape not in dictionary → `grape None`, no DB query; (3) `grape_variety=""` → empty, no `count_filters` / `search_filters` call (spy) |
| `test_product_api.py::test_search_low_uses_ocr_hint_analogs` | PA-C1b-fix1 | «КРАСНОЕ СУХОЕ» → `hints.color == "Красное"`, `wines == []`, `total 0`, `filters.color/grape None` |
| `…::test_search_low_ocr_grape_analogs` (sibling, new) | PA-C1b2-fix1 | «КАБЕРНЕ СОВИНЬОН» → `ocr_filters`, non-empty, winner excluded, all wines contain the grape |
| `…::test_search_low_rerank_switch_no_grape_empty` (renamed) | PA-C1d-fix1 | rerank → rank 2, «2019» → `ocr_filters`, empty; + grape line → `exclude_slugs == [rank-2 slug]`, not in wines. **DEF-1 closed as obsolete.** |
| `…::test_found_analogs_endpoint` | PA-C2c-fix1 | `source == "winner_filters"` only, `filters.color is None`, `ocr_ran False` |

## B. New tests — analogs

| Test | [TEST-ID] | Checks |
|---|---|---|
| `test_product_service_db.py::test_analogs_found_makes_no_ocr_call` | PA-B3c-fix1 | `runtime.get_ocr` + `catalog_service.recognize_crop` patched to raise/count → 0 OCR calls |
| `…::test_analogs_found_blend_uses_first_grape` | PA-B3d-fix1 | blend winner (`,` / `/`) → filter = canonical first element, ≠ second |
| `…::test_analogs_limit_and_total` | PA-B3e-fix1 | limit 1/2/5: `total == find_wines(ALL).total`, page = prefix of `find_wines` order (rating DESC NULLS LAST) |
| `…::test_repo_grape_aliases_keys_in_dictionary` | PA-B6-fix1 | every `product.yaml` `grape_aliases` key is in the DB grape dictionary |
| `…::test_unknown_grape_alias_key_warned_and_ignored` | PA-B6b-fix1 | unknown key → WARNING (caplog) + ignored; known key kept |
| `…::test_repo_grape_aliases_no_startup_warning` | PA-B6c-fix1 | prod aliases → no `grape_aliases` warning at service start |
| `test_product_api.py::test_search_low_latin_grape_analogs` | PA-C1e-fix1 | «CABERNET SAUVIGNON» / «RED DRY WINE» → grape «Каберне Совиньон», `color None`, `hints.color "Красное"`, winner excluded |
| `…::test_search_not_found_without_grape_empty` | PA-C1f-fix1 | not_found + «ROSSO 2019» → empty, `total 0`, `exclude_slugs []` |
| `…::test_search_low_ocr_unavailable[4]` | PA-C1g-fix1 | policy `ocr_unavailable` / `ocr_failed` (service does not call OCR again), `get_ocr → None`, engine raises `OCRUnavailableError` → 200, `ocr_ran False`, empty |
| `test_product_hints.py::test_grape_aliases_latin[10]` + `_pinot_gris_not_noir`, `_key_outside_dictionary_ignored` | PA-A5/A5b/A5c-fix1 | SANGIOVESE → Санджовезе; PINOT NOIR / Pinot Nero / NERO PINOT → Пино Нуар; PINOT / ПИНО → []; PINOT GRIS → Пино Гри (not Нуар); CABERNET SAUVIGNON; GEWÜRZTRAMINER (diacritics) |
| `…::test_grape_aliases_absent_backward_compatible[14]` | PA-A5d-fix1 | `grape_aliases` None / `{}` → identical to the pre-fix1 call |
| `…::test_extract_hints_with_aliases`, `…_repo_product_yaml_grape_aliases_load`, `…_grape_aliases_validation[2]` | PA-A5e/f/g-fix1 | aliases wired through `extract_hints`; repo `product.yaml` loads; empty key / alias → `ValidationError` |

## C. New tests — OCR fallback chain (no GPU / LLM / network)

`tests/test_ocr_selection.py` (21): pure `select_ocr_engine` (phocr+CUDA → `phocr`/`cuda_available`, probe not called; no CUDA → `llm`/`no_cuda`; missing key → `none`, `llm_unavailable…`, `engine None`; `llm` probes regardless of CUDA, failure → `none`; `mock` → no probe; unknown → `ValueError`); real LLM factory without key → reason names only the variable; fake key value set → never in reason / caplog (success and failing-init paths); `cuda_available`: `device=cpu` → False, CPU-only session → False even with `ort.get_available_providers()` listing CUDA, CUDA session → True; `DinoOnnxEncoder.active_providers` reads the existing session; `build_eval_runtime` with fakes: GPU path `create_ocr_engine("phocr", use_cuda=True, lang, limit_side_len, ort_threads, llm_task)` exactly once and lazily; no-CUDA → LLM engine, no PHOCR; `none` → `get_ocr() is None`, no retry; mock; exactly one INFO `OCR engine: configured=phocr effective=… reason=…` (3 cases).

`tests/test_policy_decision.py` (+5): `ocr_factory → None` → top-1, `rerank_triggered False`, `ocr_unavailable`; `OCRUnavailableError` → `ocr_failed`; `RuntimeError` / `OSError` propagate; large margin → factory not called. Existing 2B-01..04 unchanged, green.

`tests/test_ocr_adapter.py` (+4): `complete` raising `openai.APIConnectionError` / `RuntimeError` → `OCRUnavailableError` with `__cause__`; missing crop → `FileNotFoundError` (engine not called); unrelated `TypeError` not masked.

`tests/test_eval_predict_api.py` (+2): real `predict_slug` → `run_search` → `decide` with only retrieve/OCR faked; `get_ocr → None` and failing LLM OCR → 200 `{"slug": top-1}`, reranker not called; decision-log line has `score_1`, `score_2`, `rerank_reason` (`ocr_unavailable` / `ocr_failed`), `rerank_triggered false`.

## D. Regression

- **eval_ocr_gate:** `scripts/eval_ocr_gate.py --margins 0.08` run twice on copies of `agent_docs/reports/ocr_lines_dev_crops.json` (cache complete → no OCR engine built, cache unchanged): HEAD src and pre-fix1 src exported from `0d8cbdb` (`data/tmp/test_fix1_pre/`, loaded first on `sys.path`). Both exit 0; `data/tmp/test_fix1_gate_{pre,post}.json` byte-identical (`cmp`). `confident` 49/51, `always` 45/51 at 0.08.
- **Decision log:** eval lines contain `score_1`, `score_2`, `rerank_reason` (FIX1-E1 + existing PA-D3); product lines `search_id`, `status` (existing PA-D3b) — green.
- **owner_eval sets 1/2:** not re-run (owner decision E). Compared the Coder's existing GPU files `data/tmp/after_fix1_set{1,2}.jsonl` vs `data/tmp/baseline_master_set{1,2}.jsonl` by `query_id`: `predicted_slug` **27/27 + 25/25 = 52/52 identical**, same query ids; only `latency_ms` differs.

## Defects

None.

## Notes / open questions (non-blocking)

- The `OCR engine:` startup line is not printed under plain `uvicorn` (no app logging handler; pre-existing, `main.py` out of fix1 scope) — covered via `caplog` (FIX1-C8). Candidate backlog item for @Coder/@Planner.
- `llm_unavailable: <Type>: <message>` embeds the full init error text; safe today because `llm/factory.py` messages name only the env variable (tested with a fake key value). Any future factory error that interpolates config values would leak into the log — worth keeping in mind for reviews.
- FIX1-O3 (unrelated exceptions not wrapped into `OCRUnavailableError`) asserts current behaviour, which matches `ocr_engine.md` («only this type caught»); not a contract line by itself.

## Files changed (tests only)

`tests/test_product_service_db.py`, `tests/test_product_api.py`, `tests/test_product_hints.py`, `tests/test_policy_decision.py`, `tests/test_ocr_adapter.py`, `tests/test_eval_predict_api.py`, `tests/product_helpers.py`, new `tests/test_ocr_selection.py`. Artifacts: `data/tmp/test_fix1_*` (gate JSON/logs, OCR cache copies, pre-fix1 src export, full pytest log).
