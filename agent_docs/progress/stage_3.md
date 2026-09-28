# Progress — Stage 3/4 (Product API + Web UI)

Append-only. Plan: `agent_docs/plans/web_product.md`.

## 2026-09-28 — Coder (PROD-000)

- STATUS: READY (PROD-000)
- Added: `src/core/product/{__init__,schemas,service,stub}.py`, `config/product.yaml`,
  `ProductSettings` + `load_product_settings()` in `src/core/config.py`; lifespan in
  `src/api/main.py` sets `app.state.product_settings` and `app.state.product_service = StubProductService()`
- `.gitignore`: no change needed (`data/` already ignored → covers `data/tmp/search_queries/`, `data/tmp/search_feedback.jsonl`)
- Commands: `ruff check src/` exit 0; `mypy src/core/product/ --ignore-missing-imports` exit 0;
  `pytest tests/ -k "not owner_eval"` → 71 passed, 11 failed (identical on baseline without PROD-000 changes:
  `test_policy_confident` ×9, `test_catalog_load` wine count 2091≠1950, `test_wine_repository` filter — DB/catalog data drift)
- Smoke: stub `search` found / low / not_found (`x_notfound.jpg` → `winner=None`, analogs non-empty), JSON round-trip OK;
  `uvicorn` start OK, `/v1/eval/predict` returns `{"slug": ...}`
- Open question (non-blocking): contract «color» vs DB `wines.color` (shade) / `categories.name` → `agent_docs/reports/BLOCKED.md`

## 2026-09-28 — PROD-000 follow-up (owner decisions)

- Color = `categories.name`: contract §2/§4.3/§5/§6 + `web_ui.md` + `coder_product_api.md` updated;
  DTO `WineCard.shade` added, `CatalogFilters.category` / `Dictionaries.categories` removed; stub + `product.yaml` (`Оранжевое`) aligned
- No fixed catalog sizes in tests/docs: `test_catalog_load` (non-empty instead of 1932/18/153/1950),
  `test_wine_repository` (limit = catalog size instead of 50), `manual_testing.md`, `tester_1_2_catalog_load.md`
- `test_policy_confident`: pin `margin_min=0.08` in test policy (prod `ocr_rerank.yaml` is 0.01 → synthetic 0.02 gaps skipped OCR)
- Commands: `ruff check src/ tests/` exit 0; `mypy src/core/product/` exit 0; `pytest tests/ -k "not owner_eval"` 82 passed; `-k owner_eval` 4 passed

## 2026-09-28 — Coder (PROD-API, `feat/product-api`)

- STATUS: READY_FOR_TEST (PROD-API)
- API-001: `api/eval_pipeline.run_search(runtime, path, log_fields=...)` → `SearchRun(bundle, decision, latency_ms)`; `predict_slug` uses it;
  model calls serialized by a module lock. Decision log: `score_1`, `score_2` always; product adds `search_id`, `status`,
  `confidence_level`, `endpoint: "product"` (+ `original_name`).
- API-002: `core/product/catalog_service.py::CatalogProductService` (+ pure `hints.py`, `storage.py`, `vocabulary.py`);
  `WineRepository.search_filters` gains `exclude_manufacturer`, `exclude_slugs`, `grape_names_any` (whole element of
  `grape_variety` split on `,;/+`), `dishes_any`; new `count_filters` (same filters). Existing params unchanged.
- API-003: `api/main.py` stub → `CatalogProductService` + `product` router; `api/routers/product.py` — §5 endpoints,
  streamed upload to `data/tmp/uploads` with size check, content-type + Pillow decode check, `run_in_threadpool`.
- API-004: `scripts/cleanup_search_queries.py` (`--dry-run`, `--days`), `scripts/calibrate_confidence.py`
  (HTTP or `--in-process [--ocr-device cpu]`) → `agent_docs/reports/confidence_calibration.md`. `product.yaml` NOT changed.
- API-005: `manuals/architecture.md` (product flow, analogs, dictionaries, storage), `manuals/configuration_guide.md`
  (`product.yaml`, calibration, cleanup), `manuals/quickstart.md` (`/api/v1` curl), `ARCHITECTURE.md` §4–5 «готово», README endpoints.
- Environment note: GPU held by the :8080 server (7.6/8 GB) → :8081 hit CUDA OOM; ran :8081 with `CUDA_VISIBLE_DEVICES=""`
  (ORT CPU fallback, configs untouched). PHOCR text recognition hardcodes CUDA in beam search → OCR-dependent requests
  return 500 on that CPU-only server (environmental; verified the same paths in-process with in-memory `compute.device=cpu`).

Verification (worktree `.worktrees/api`, `UV_PROJECT_ENVIRONMENT=../../.venv UV_NO_SYNC=1`):

| Command | Exit |
|---|---|
| `uv run ruff check src/ scripts/cleanup_search_queries.py scripts/calibrate_confidence.py` | 0 |
| `uv run mypy src/core/product/ src/api/ --ignore-missing-imports` | 2 — pre-existing: pyproject `python_version=3.11` vs numpy stubs (syntax) |
| `uv run mypy src/core/product/ src/api/ --ignore-missing-imports --python-version 3.12` | 1 — 0 errors in `core/product`, `api`; 9 pre-existing in `core/config`, `core/text`, `core/policy`, `db/repository` (`list` method shadowing), `llm` |
| `uv run bandit -r src/ -ll` | 0 |
| `timeout 900 uv run pytest tests/ -v` | 0 (86 passed) |
| `participant_test.sh` set 1 / set 2 → `:8081/v1/eval/predict` → `data/tmp/after_product_api_set{1,2}.jsonl` | 0 / 0 |
| `uv run python scripts/cleanup_search_queries.py --dry-run` / real / `--days -1` | 0 / 0 / 2 |
| `CUDA_VISIBLE_DEVICES= uv run python scripts/calibrate_confidence.py --in-process --ocr-device cpu --report agent_docs/reports/confidence_calibration.md` | 0 |

- Eval regression vs `data/tmp/baseline_master_set{1,2}.jsonl`: set 1 — 27/27 slugs identical (hit@1 26/27 = master);
  set 2 — 23/25 identical on :8081; the 2 others (q-000004, q-000020, exact image ties → OCR rerank) failed with the
  environmental PHOCR/CUDA 500; re-run in-process with OCR on CPU → both equal baseline. Net: 52/52 identical, set 2 hit@1 25/25.
- Live curl on :8081: `POST /search` 200 (found/high, photo + JSON persisted), `GET /search/{id}` 200, `/analogs` 200
  (`winner_filters`, grape dropped → color-only fallback, total 779), `/wines` 200 (total, rating DESC), `/wines/{slug}` 200,
  `/dictionaries` 200 (4 colors, 139 grapes, 9 regions, 6 sweetness, 33 dishes), `/feedback` 204 + JSONL line;
  errors: empty 400, undecodable 400, 16 MB 413, text/plain 415, missing field / `limit=0|51` / `offset=-1` / bad verdict 422,
  unknown wine / search / analogs / feedback 404. Noise image → `low` + `vector` analogs.
- Calibration (not applied): 52 queries, hit@1 51, hit@5 52; hits score_1 min 0.668 / p10 0.793 / median 0.874; 1 miss 0.825.
  Suggested `high_min` 0.83, `medium_min` 0.79 (weak: one miss); `not_found_min` TODO (no out-of-catalog photos; synthetic
  non-wine images score 0.55–0.59 > current 0.50).
- `ocr_filters` checked in-process (no models; real DB dictionaries): AGORA label lines → `Красное` + `Каберне Совиньон`
  (total 244); «СКАЛИСТЫЙ БЕРЕГ / СУХОЕ КРАСНОЕ» → color only; «белого / Шардоне» → `Белое` + `Шардоне`; no hints → `vector`.
  Fixed on the way: manufacturer hint picked a fuzzy false positive («А. Гордиенко & М. Николаев» for «AGORA», compact
  score 0.89 ≥ 0.85) — matches are now ranked by share of name words found verbatim in OCR, then length.
- Not live-verified over HTTP: `ocr_filters` via `POST /search` (needs a low-confidence real label photo with OCR on GPU).
- Handoff → @Tester: `agent_docs/instructions/tester_product_api.md`.

## 2026-09-28 — Tester (PROD-API, `feat/product-api`)

- STATUS: TEST_FAIL (PROD-API) — 1 defect (DEF-1: `vector` analogs contain the winner when OCR rerank switched it to rank ≥2); all other items pass, 0 env-skips.
- Report: `agent_docs/reports/test_product_api.md`; contract question appended to `agent_docs/reports/BLOCKED.md`.
- New tests (119): `tests/test_product_{hints,status,storage,service_db,api,api_live,decision_log}.py` + `tests/product_helpers.py`; marker `db` registered in `tests/conftest.py`.
- A 65/65 · B 16/16 · C 34/35 (fail: `test_product_api.py::test_search_low_rerank_switch_vector_excludes_winner`) · D 3/3 + regression.

| Command | Exit |
|---|---|
| `uv run ruff check src/ tests/` | 0 |
| `timeout 1200 uv run pytest tests/ -v -rs` | 1 — 204 passed, 1 failed, 0 skipped (205) |
| `participant_test.sh` set 1 / set 2 → `:8081` (CPU-only) → `data/tmp/test_product_api_set{1,2}.jsonl` | 0 / 0 |
| in-process CPU OCR `predict_slug` set 2 `q-000004`, `q-000020` | 0 |
| `scripts/eval_ocr_gate.py --margins 0.08` branch / master | 0 / 0 (JSON identical) |

- Regression: set 1 27/27 = master; set 2 23/25 over HTTP + 2 OCR queries (HTTP 500: PHOCR needs CUDA on CPU-only server, env) = baseline in-process → 52/52 identical, hit@1 51/52 unchanged.
- Decision log: 52 eval lines with `score_1`/`score_2`, no product fields; product line has `search_id`, `status`, `confidence_level`.
- Next: Planner answers BLOCKED question → @Coder fixes DEF-1 → re-run `tests/test_product_api.py`.

## 2026-09-28 — Planner (PROD-API owner decisions → fix1, `feat/product-api`)

- DECISION (owner, 2026-09-28): analogs = same grape only. Found → `winner_filters` from DB (winner's first grape,
  `exclude_manufacturer`, `exclude_slugs`), no OCR, color/region not applied. Low / not_found → `ocr_filters` with the
  OCR grape only (Latin/transliterated names mapped; product-only `analogs.grape_aliases` in `product.yaml`); no grape
  or 0 matches → empty, `total=0`. No color-only retry, no `vector` (kept in `AnalogSource` as reserved; stub may use it).
- DECISION (owner): OCR engine chain at startup — `phocr` + CUDA → PHOCR (GPU path byte-identical); no CUDA → LLM OCR
  (`ocr_label`); LLM unavailable / per-request LLM failure → no OCR (rerank skipped, unknown-wine analogs empty).
  No config default changes, no new packages (profiles → CFG-DEVICE-001). Out of scope: live GPU re-verification,
  `product.yaml` threshold changes, UI merge.
- Contracts: `product_api.md` §2 note, §3 stub note, §4.1 step 5, §4.2 rewritten (+ «UI impact»), §6 `grape_aliases`;
  `ocr_engine.md` «Engine selection». `web_ui.md` not edited (lives in `feat/web-ui`).
- BLOCKED.md PROD-API question (DEF-1) → RESOLVED as obsolete.
- INSTRUCTIONS_READY (PROD-API-FIX1): `agent_docs/instructions/coder_product_api_fix1.md` → `tester_product_api_fix1.md`.

## 2026-09-28 — @Coder (PROD-API-FIX1, `feat/product-api`)

- FIX1-001 analogs (`core/product/catalog_service.py`): found → `winner_filters` (winner's first grape, canonical;
  `exclude_manufacturer`, `exclude_slugs=[winner]`, no color; hints = winner color + grape, `ocr_ran=False`, no OCR call);
  low / not_found → `ocr_filters` (first OCR grape only, `exclude_slugs=[winner]` if any, no color). `grape is None` →
  empty without DB query; 0 matches → empty, no retry. `_vector_analogs` + color-only retry removed; `candidates` param
  dropped; `grep '"vector"'` empty. `_hints`: `rerank_reason in {ocr_unavailable, ocr_failed}` / no engine /
  `OCRUnavailableError` → `OcrHints(ocr_ran=False)` (one WARNING, no stack trace).
- FIX1-002 grapes: `ProductSettings.analogs.grape_aliases` (default `{}`, validated); `config/product.yaml` filled for 68
  dictionary grapes (keys checked against the 139-grape DB dictionary; unknown keys → startup WARNING + ignored — none at
  startup). `extract_grapes` / `extract_hints(grape_aliases=None)`: whole-phrase alias match (fold, token order free),
  alias → its key only; union with `label_evidence`, same ordering. Checked: CABERNET SAUVIGNON → Каберне Совиньон;
  SANGIOVESE → Санджовезе; PINOT NOIR → Пино Нуар; «ПИНО» / «PINOT» → none. Confidence thresholds untouched.
- FIX1-003 OCR chain: `core/ocr/base.py::OCRUnavailableError`; `core/ocr/selection.py::select_ocr_engine` (pure);
  `DinoOnnxEncoder.active_providers` (existing session, no new sessions); `build_eval_runtime` selects once, stores
  `ocr_effective` / `ocr_reason`, logs `OCR engine: configured=… effective=… reason=…`; `get_ocr() -> IOCREngine | None`
  (phocr lazily with the same args); `LLMOCREngine.recognize` → `OCRUnavailableError` on OpenAI / RuntimeError;
  `decide(ocr_factory -> IOCREngine | None)`: None → `ocr_unavailable`, `OCRUnavailableError` → `ocr_failed` (only this
  type caught); `recognize_crop -> list[str] | None`; `calibrate_confidence.py` help/docstring only. No decision-log
  field added.
- FIX1-004 manuals: `architecture.md`, `configuration_guide.md`, `quickstart.md`, `manual_testing.md` §5.

| Command | Exit |
|---|---|
| `uv run ruff check src/` | 0 |
| `uv run ruff check scripts/calibrate_confidence.py` (whole `scripts/`: 62 pre-existing errors in untouched scripts) | 0 |
| `uv run mypy src/core/product/ src/core/ocr/ src/api/ --ignore-missing-imports --python-version 3.12` | 1 — 9 errors, all pre-existing (same 9 on HEAD), 0 new |
| `uv run bandit -r src/ -ll` | 0 |
| `timeout 1200 uv run pytest tests/ -q` | 1 — 195 passed, 8 failed (expected, old behaviour), 2 skipped |
| API `:8081` GPU → `OCR engine: configured=phocr effective=phocr reason=cuda_available` | — |
| `participant_test.sh` set 1 / set 2 → `:8081` GPU → `data/tmp/after_fix1_set{1,2}.jsonl` | 0 / 0 |
| slugs vs `data/tmp/baseline_master_set{1,2}.jsonl` | 27/27 + 25/25 = **52/52 identical** (2 PHOCR reranks ran) |
| API `:8081` `CUDA_VISIBLE_DEVICES=""` → `effective=none reason=llm_unavailable: ValueError: Environment variable 'QWEN_API_KEY' is missing or empty (…)`; `/v1/eval/predict` → slug | 0 |

- Live: found `agora-muskat-chernyj` → `/analogs` = `winner_filters`, grape Мускат, color null, excl. AGORA WINERY, 5 wines
  by rating (total 30); found Пино Нуар (Chateau Andre) → 5 other manufacturers, total 216. In-process: low + «SANGIOVESE /
  ROSSO» → `ocr_filters`, grape Санджовезе, color None, total 12; «2019» / no engine / `ocr_failed` → empty, total 0.
- Old-behaviour tests now failing by design (→ @Tester `tester_product_api_fix1.md`):
  `test_product_api.py::test_search_low_uses_ocr_hint_analogs` (color-only hint → expects color filter),
  `test_product_api.py::test_search_low_rerank_switch_vector_excludes_winner` (expects `vector`),
  `test_product_service_db.py::test_analogs_for_found_winner_filters` (expects `filters.color == winner.color`),
  `::test_analogs_ocr_filters_color_and_grape`, `::test_analogs_fallback_impossible_grape_to_color`,
  `::test_analogs_fallback_impossible_color_to_vector`, `::test_analogs_no_hints_vector`,
  `::test_analogs_winner_fallback_chain`.
- Note: app INFO logs (incl. the `OCR engine:` line and the existing `eval runtime ready`) are not printed by plain
  `uvicorn api.main:app` — no handler is configured for app loggers (pre-existing; `main.py` out of fix1 scope). Verified
  via the same app started with `logging.basicConfig(level=INFO)` + `uvicorn.run(...)`.

READY_FOR_TEST (PROD-API-FIX1)
