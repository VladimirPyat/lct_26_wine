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

## FIX-WEB-02 — shops map demo stub (@BugFixer, 2026-09-29)

- «Найти в магазинах рядом» on the result page is now an openable demo: native `<dialog>`, 3×3 OSM tiles (zoom 15)
  around geolocation (fallback central Moscow), 6–8 random shops with prices 900–1200 ₽, cheapest highlighted +
  caption + sorted list, badge «Демо — цены и магазины случайные», OSM attribution. Client-side only
  (`src/web/static/js/shops_map.js`); no API/backend changes; `tile.openstreetmap.org` owner-approved for this stub only.
- `scripts/dev_ui_stub.py` — UI preview on `StubProductService` (127.0.0.1:8082); documented in `manuals/quickstart.md`.
- Tests: `tests/web/test_shops_map.py` (new), D-3 allowlist for the two approved OSM URLs;
  `pytest tests/web/` 129 passed, 1 xfailed; full suite: 9 failures = Postgres not running (unrelated).
- Report: `agent_docs/reports/bug_web_shops_map.md`; @Planner: record web_ui.md §3/§6 external-host exception.

FIXED (FIX-WEB-02 shops map stub)
