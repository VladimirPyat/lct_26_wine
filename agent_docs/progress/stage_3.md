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
