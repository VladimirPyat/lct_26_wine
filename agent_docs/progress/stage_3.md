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
