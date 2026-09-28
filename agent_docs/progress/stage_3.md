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

## 2026-09-28 — @Tester (PROD-API-FIX1, `feat/product-api`, code `2eace1e`)

- A: 8 old-chain tests rewritten to §4.2 (IDs kept, `-fix1`), PA-C2c tightened to `winner_filters` only; DEF-1 closed as obsolete
  (PA-C1d-fix1). B: found analogs (no OCR call, blend first grape, limit/total), Latin grape / no grape / OCR unavailable in
  `search`, `grape_aliases` (pure + DB keys + unknown-key warning). C: new `tests/test_ocr_selection.py` (selection, CUDA
  detection, runtime wiring, startup log, no secret leak), policy `ocr_unavailable` / `ocr_failed` / PHOCR errors propagate,
  LLM adapter → `OCRUnavailableError`, `/v1/eval/predict` with no OCR → top-1.
- D: `eval_ocr_gate.py --margins 0.08` HEAD vs pre-fix1 `0d8cbdb` src → both exit 0, JSON byte-identical; owner_eval not
  re-run (owner decision E) — existing `after_fix1_set{1,2}` vs `baseline_master_set{1,2}`: 52/52 `predicted_slug` identical.

| Command | Exit |
|---|---|
| `uv run ruff check src/ tests/` | 0 |
| `timeout 1200 uv run pytest tests/ -v -rs` | 0 — 278 passed, 0 failed, 2 skipped (live e2e: no server on :8081) |

- Defects: none. Report: `agent_docs/reports/test_product_api_fix1.md`.

TEST_PASS (PROD-API-FIX1)

## 2026-09-28 — Coder (WEB-UI, branch `feat/web-ui`, worktree `.worktrees/web`)

- STATUS: READY_FOR_TEST (WEB-001 … WEB-007)
- Added `src/web/`: `__init__.py` (exports `router`, `STATIC_DIR`), `router.py` (pages `/`, `POST /search`,
  `/result/{id}` [+`?analogs=1`, `?fb=1&verdict=`], `/result/{id}/photo`, `POST /result/{id}/feedback`, `/wine/{slug}`,
  `/catalog`, `/me`; route class renders `error.html` on unhandled errors), `views.py` (dataclass view models,
  catalog URLs/chips), `templating.py` (autoescape, `StrictUndefined` when `VINE_WEB_STRICT=1`; filters
  `confidence_label`, `rating_glasses`, `rating_text`, `num`, `is_http_url` + test `http_url`);
  templates `base.html`, `components/{wine_card,confidence_badge,analogs,feedback,stub_feature,filters}.html`,
  `pages/{scan,result,wine,catalog,me,error}.html`; static `css/{tokens,app}.css`,
  `js/{ui,upload,camera,lightbox,store}.js`, `img/` (prototype assets + `bottle_placeholder.svg`)
- `src/api/main.py`: only `app.mount("/ui-static", …)` + `app.include_router(web_router)` (stub line untouched)
- Manuals (RU): `quickstart.md` (UI run, stub file-name states, HTTPS for phone camera), `architecture.md` (UI layer,
  stub vs real service), `manual_testing.md` (UI checklist stub), `index.md` synced
- Deviations: `candidate_strip.html` not created (contract §3: candidates are not shown in UI); extra `js/ui.js`
  (filters slide-over, «Скоро» toast, image fallback); extra localStorage key `svoe_vino:v1:titles` (slug→title cache
  for /me lists); feedback redirect is `?fb=1&verdict=<v>#feedback` (verdict needed for the mismatch state);
  upload type decided by content signature (JPEG/PNG/WebP magic) ∩ `upload.content_types`, declared type only picks
  400 vs 415 for undecodable files
- Commands: `uv sync --extra ml --extra db --extra dev` (from lock, no changes to pyproject/uv.lock);
  `uv run ruff check src/web/ src/api/main.py` exit 0; `uv run mypy src/web/ --ignore-missing-imports` → 1 error in
  `src/core/config.py:8` (pre-existing unused `type: ignore`, file untouched), `src/web` clean;
  `uv run pytest tests/ -v -k "not owner_eval"` → 82 passed, 4 deselected
- Smoke (TestClient, `VINE_WEB_STRICT=1`, app = web_router + `/ui-static` + StubProductService + load_product_settings):
  all pages 200; found/low/not_found states, `?analogs=1`, photo (private cache), feedback PRG match/mismatch,
  404 (bad/unknown id, unknown slug, unknown photo), upload 400 empty/no file/garbage, 413 >15 MB, 415 text/gif,
  PNG + WebP(octet-stream) accepted, temp uploads cleaned, catalog filters/chips/empty/exclude/bad page,
  autoescape + `javascript:` product_url hidden, 500 page without trace. Real app on :8082 also starts (full lifespan).
- Screenshots: 49 PNG in `agent_docs/reports/web_ui_screens/` (gitignored) — 9 pages × 360×740, 390×844, 768×1024,
  1280×800, 1920×1080 + filters panel open, /me guest/favorites, wine logged-in; headless Chromium via CDP;
  `scrollWidth > innerWidth` = false on all 45 page×size shots
- Known limitation: app-level 404 for paths outside web routes (e.g. `/etc/photo`) stays FastAPI JSON (no app
  exception handler — main.py scope restricted)

READY_FOR_TEST (WEB-UI)

## WEB-UI — @Tester (A–D, 2026-09-28)

- Branch `feat/web-ui`; tests `tests/web/{conftest,web_helpers,test_pages,test_search_flow,test_catalog_analogs,test_security}.py`
  (TestClient on web_router + /ui-static + StubProductService / local fakes, `VINE_WEB_STRICT=1`, no lifespan/DB)
- A 14 passed · B 32 passed · C 16 passed + 1 xfailed · D 64 passed
- `uv run ruff check src/web/ tests/web/` exit 0; `uv run pytest tests/web/ -v` 126 passed, 1 xfailed;
  `uv run pytest tests/ -v -k "not owner_eval"` 208 passed, 4 deselected, 1 xfailed
- BUG-WEB-01 (minor): analogs block not capped at 5 cards when service returns more (`views.build_analogs_view`);
  strict xfail `test_c2_ui_caps_cards_even_if_service_returns_more`. Note N-1: `image_url` unchecked in lightbox href
- Report: `agent_docs/reports/test_web_ui.md`; §E pending on master

TEST_PASS (WEB-UI A–D)

## 2026-09-28 — Merge to `master` (PROD-API + WEB-UI)

- Merged `feat/product-api` (--no-ff), then `feat/web-ui`; conflicts resolved: `src/api/main.py` (real `CatalogProductService` + both routers `product` / `web` + `/ui-static`), `manuals/{architecture,quickstart}.md` and this file (both sections kept).
- UI now runs on the real service (no stub in lifespan). Owner decisions applied in UI: empty analogs → «Аналог подобрать не удалось»; `winner_filters` analogs → sommelier hint. `tests/web/test_catalog_analogs.py::test_c2_empty_analogs` text updated accordingly.
- Commands: `ruff check src/ tests/` exit 0; `pytest tests/ -q` exit 0 — 404 passed, 2 skipped (live e2e), 1 xfailed.
- Smoke on :8080 (GPU): `/health`, `/`, `/catalog`, `/me`, `/docs`, `/api/v1/dictionaries`, `/api/v1/wines` 200; `/v1/eval/predict` returns slug; `/api/v1/search` found/high; UI form `POST /search` → 303 → result (found) → `?analogs=1` (298 matches, sommelier hint) → photo 200 → wine page 200; noise image → low + «Аналог подобрать не удалось».
- Eval runs — owner. Open: app logging config (OCR engine line invisible under plain uvicorn), `not_found_min` calibration on real out-of-catalog photos.

## 2026-09-28 — Logging, fp16 encoder, full quickstart (master)

- App logging: `src/api/main.py` configures root logger (stderr, `VINE_LOG_LEVEL`, default INFO) unless handlers exist → startup lines (encoder, `OCR engine: …`, dictionaries) visible under plain uvicorn.
- Encoder config → `bin/siglip2_wine_p1_epoch_3_fp16.onnx` (owner links); DB index built with fp32 kept (same space). owner_eval via :8080 with fp16: set1 27/27, set2 25/25 identical to master baseline.
- Catalog inputs tracked in git: `data/wines_integrated_updated.csv` (2103 wines), `data/wines_problem_images.csv` (100), `data/site_database/wines_database_enriched.json` (rating/dishes/url); defaults of `rebuild_catalog_db.sh` / `prepare_clean_csv.py` → `data/wines_integrated_updated.csv`. Dry-run prepare: ready=2091, rejected=12.
- Docs: `manuals/quickstart.md` rewritten (Docker, NVIDIA driver, uv, models + links, DB, indexing, run/open UI, API, eval, troubleshooting); new `manuals/user_interface.md`; README (docs, UI + API endpoints, layout), `manuals/index.md`, `configuration_guide.md`, `ARCHITECTURE.md`, `manual_testing.md` synced.
- Commands: `ruff check src/ tests/` exit 0; `pytest tests/ -q` exit 0 — 404 passed, 2 skipped, 1 xfailed.

### 2026-09-28 — isolated GPU Docker run (master)

- New `Dockerfile` (python:3.12-slim + uv 0.9.24, `uv sync --frozen --extra ml --extra db` → swap to `onnxruntime-gpu` via `requirements-gpu.txt`, CUDA 13/cuDNN 9 pip libs on `LD_LIBRARY_PATH`; CMD = `alembic upgrade head` + uvicorn :8080) and `docker-compose.full.yml` (project `vine`: `db` pgvector without published port + `app` with GPU reservation; `bin/` ro, `data/`, `static/wines/` bind mounts, `phocr_models` volume). `.dockerignore` rewritten. No CPU container (owner: test on GPU; CPU = DB-only compose + host app).
- `src/api/main.py`: PHOCR warm-up in lifespan (first start downloads ~270 MB weights; previously the first rerank request hit the customer script 60 s timeout). Healthcheck start-period 300 s.
- Verified: image build OK; in-container `rebuild_catalog_db.sh --yes` ≈10 min on GPU → 2091|2091; app log CUDA EP + `OCR engine … effective=phocr` + `PHOCR ready`; `/`, `/catalog`, `/docs` 200; customer script vs container: set1 27/27, set2 25/25 identical to master baseline (max latency 1.6 s). Windows / Docker Desktop path not tested.
- Docs: `manuals/quickstart.md` restructured (Part 1 short Docker GPU guide: requirements via links, DB, run, customer script endpoint, UI/manual testing links; Part 2 DB-only + host app; Part 3 details); README, `manuals/index.md`, `architecture.md` (deployment section), `configuration_guide.md` synced.
- Commands: `ruff check src/` exit 0; `pytest tests/ -q` — 404 passed, 2 skipped, 1 xfailed.
