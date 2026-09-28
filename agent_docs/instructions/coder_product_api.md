# @Coder — PROD-API: real `ProductService` + `/api/v1/*`

**Branch:** `feat/product-api` (worktree `../lct_vine_api`, API port 8081). Starts from `master` with PROD-000.  
**Plan:** [`../plans/web_product.md`](../plans/web_product.md) · **Contract:** [`../contracts/product_api.md`](../contracts/product_api.md) §4–7  
**Do not touch:** `src/web/`, `tests/web/`, DTO/Protocol shapes (contract change → Planner / `BLOCKED.md`).

## Steps

### API-001 — Shared pipeline (no behaviour change for eval)

- Extract retrieve → decide → log from `api/eval_pipeline.py` into a reusable function (e.g. `run_search(runtime, path) -> (bundle, decision, latency)`); `predict_slug` uses it. Decision log: add `score_1`, `score_2` always; product calls add `search_id`, `status`, `confidence_level`, `endpoint: "product"`.
- Regression: owner_eval sets 1/2 via `/v1/eval/predict` give the same slugs as before (compare with `data/owner_eval/*/predictions.jsonl` produced before the change).

### API-002 — `CatalogProductService` (`src/core/product/catalog_service.py`)

- Constructor takes `EvalRuntime` + `ProductSettings`; builds dictionaries at init (§4.3) and runs retention cleanup (§4.4).
- `search` per §4.1 (status / level from `product.yaml`), persistence `{id}{ext}` + `{id}.json`.
- `get_search` / `query_photo_path` validate id `^[0-9a-f]{32}$`.
- `get_wine`, `find_wines` → `WineRepository` (`CatalogFilters.color` maps to the existing `category_name` filter — color = `categories.name`, contract §2; add `exclude_manufacturer` / `exclude_slugs` filters to `search_filters`, plus a `count` variant; keep existing params working). Sort `public_rating DESC NULLS LAST`, then `id`.
- `analogs_for` / analogs inside `search` per §4.2, reusing OCR lines when present, `FuzzyReranker` helpers and `ocr_rerank.yaml` aliases for hints. Keep hint extraction in a pure module (e.g. `core/product/hints.py`) — testable without DB/OCR.
- `record_feedback` → JSONL append (§4.5), file lock not required (single process) but write whole line at once.
- DB sessions via `session_scope(runtime.session_factory)` per call.

### API-003 — Wiring + routes

- `src/api/main.py`: replace the stub line with `CatalogProductService(app.state.eval_runtime, app.state.product_settings)`; include `product` router. Nothing else in `main.py`.
- `src/api/routers/product.py`: endpoints §5; upload validation from `product_settings.upload` (stream to temp file under `data/tmp/uploads`, size check while streaming, content-type + Pillow/cv2 decode check); `run_in_threadpool` for service calls.

### API-004 — Retention + calibration scripts

- `scripts/cleanup_search_queries.py` (`--dry-run`, `--days` override).
- `scripts/calibrate_confidence.py` (§7): print score_1 stats for hits / misses on owner_eval, suggested thresholds; do **not** auto-edit YAML. Record output in `agent_docs/reports/confidence_calibration.md`.
### API-005 — Docs (Russian)

`manuals/architecture.md` (product flow, analogs, storage), `manuals/configuration_guide.md` (`product.yaml`), `manuals/quickstart.md` (curl examples for `/api/v1/search`), `ARCHITECTURE.md` §4–5 status «готово». README endpoint list.

## Verification

```bash
uv run ruff check src/ scripts/cleanup_search_queries.py scripts/calibrate_confidence.py
uv run mypy src/core/product/ src/api/ --ignore-missing-imports
uv run bandit -r src/ -ll
uv run pytest tests/ -v
uv run uvicorn api.main:app --app-dir src --port 8081   # curl -F image=@data/owner_eval/1/queries/<file> :8081/api/v1/search
```

## Acceptance

- [ ] eval slugs unchanged on owner_eval 1/2
- [ ] `/api/v1/*` per contract; errors 400/404/413/415/422 as specified
- [ ] found / low / not_found produced by thresholds; analogs sources `ocr_filters` / `winner_filters` / `vector`; ≤5 by rating; `total` correct
- [ ] dictionaries built once at startup; grapes split and deduped
- [ ] photos + result JSON persisted; retention cleanup works; photo lookup safe against traversal
- [ ] feedback JSONL written; unknown id → 404
- [ ] calibration report written (thresholds stay placeholders unless user approves new values)
- [ ] lint / bandit clean; manuals updated

Handoff: `READY_FOR_TEST (PROD-API)` in `agent_docs/progress/stage_3.md` with commands + exit codes → @Tester `tester_product_api.md`.
