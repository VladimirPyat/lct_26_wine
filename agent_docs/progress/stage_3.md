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
