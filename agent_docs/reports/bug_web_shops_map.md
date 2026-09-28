# FIX-WEB-02 — «Найти в магазинах рядом»: demo map with random shop prices

- **Status:** VERIFIED (FIXED, tests green)
- **Class:** TRIVIAL-scope UI change (client-side only, `src/web/` + dev script + tests), tracked as a fix
- **Branch:** `feat/web-ui` (worktree `.worktrees/web`)
- **Date:** 2026-09-29

## Ticket

The result page rendered «Найти в магазинах рядом» via the generic `stub_feature(...)` macro — a disabled
«Скоро» card whose button only showed a toast. Owner asked for an openable demo map instead.

## Owner decisions

- No API / endpoint / backend changes, no new routes; pure client-side in `src/web/`.
- No libraries (no Leaflet, no packages).
- External host `https://tile.openstreetmap.org` approved **for this stub only** (plus the attribution link
  `https://www.openstreetmap.org/copyright`). No other external hosts.
- Prices/shops are random and explicitly labelled as demo.

## Root cause / what was a stub

`src/web/templates/components/stub_feature.html` → `stub_features()` called
`stub_feature('Найти в магазинах рядом', …)`: static text + `data-soon` button (toast «Скоро» from `ui.js`).
Used only from `pages/result.html` (found / low states); `pages/wine.html` does not render stubs.

## Changes

| File | Change |
|---|---|
| `src/web/templates/components/stub_feature.html` | new macro `shops_feature()`: card with «Демо» badge, button `data-shops-open` («Показать на карте», `aria-controls`), native `<dialog id="shops-dialog">` with badge «Демо — цены и магазины случайные», map container (no-JS note «Для демо-карты нужен JavaScript.»), status line, min-price caption, sorted list, OSM attribution link (`target=_blank`, `rel="noopener noreferrer"`), `Обновить` (hidden until JS) and close buttons (`<form method="dialog">`, works without JS; Esc native). «Цифровой сомелье» / «Чат» stubs unchanged. |
| `src/web/templates/pages/result.html` | loads `/ui-static/js/shops_map.js` (`type="module"`) next to `lightbox.js`. |
| `src/web/static/js/shops_map.js` (new) | wiring via `data-shops*` attributes (no inline handlers); `showModal()` (fallback `open` attr); geolocation with 3 s timeout → fallback central Moscow (55.7558, 37.6173); slippy-map math lon/lat → world pixel at zoom 15; 3×3 grid of 256 px OSM tiles centred on the location (x wraps, y range-checked, failed tiles hidden → neutral background); 6–8 random markers inside the visible viewport (spacing by rejection sampling), price 900–1200 ₽ step 10, format «1 050 ₽» (NBSP), label «Магазин N»; cheapest marker `is-min`; caption «Дешевле всего: X ₽ — Магазин N»; list sorted by price; «Обновить» re-randomizes; backdrop click closes; focus returns to the trigger. DOM via `createElement`/`textContent` only. |
| `src/web/static/css/app.css` | `.stub__soon--demo`, `.shops-dialog*`, `.shops-map*` (max 512×320, `overflow:hidden`, tiles centred), `.shops-marker` / `.is-min` (bordeaux fill, scale 1.15, z-index on top), `.shops-list*`. Brand tokens from `tokens.css`. |
| `scripts/dev_ui_stub.py` (new) | UI preview without backend: `web_router` + `/ui-static` + `/static/wines` (if dir exists) + `StubProductService` + `load_product_settings()`, uvicorn on 127.0.0.1:8082 (`--host/--port`); no lifespan/models/DB; no imports from `tests/`. |
| `manuals/quickstart.md` | subsection «Просмотр UI без бэкенда (stub)» (command, `*_low.jpg` / `*_notfound.jpg` trick, demo map note). |
| `tests/web/test_security.py` | D-3 external-URL checks: explicit allowlist of the two approved OSM URLs (comment references FIX-WEB-02, owner-approved); everything else still forbidden. |
| `tests/web/test_shops_map.py` (new) | result page has one `data-shops-open` trigger + `dialog#shops-dialog` + module script `/ui-static/js/shops_map.js` (200, JS content type), demo badge, no-JS note, attribution link rel; other two stubs still `data-soon`; JS has no `innerHTML`/`insertAdjacentHTML`. |

Not touched: `pyproject.toml`, `uv.lock`, `src/core/`, `src/db/`, `src/api/`, `config/`, BUG-WEB-01 strict xfail.

## Tests

- `uv run ruff check src/web/ scripts/dev_ui_stub.py tests/web/` → All checks passed
- `uv run pytest tests/web/ -v` → **129 passed, 1 xfailed** (xfail = BUG-WEB-01, unchanged)
- `uv run pytest tests/ -q -k "not owner_eval"` → 202 passed, 1 xfailed, **9 failed** — all 9 are
  `tests/test_wine_repository.py` / `tests/test_catalog_load.py::TestCatalogImportDb` with
  `psycopg.OperationalError: connection refused 127.0.0.1:5432` (Postgres container not running; unrelated to this fix).

## Smoke

- `uv run python scripts/dev_ui_stub.py` → `GET /` 200; `POST /search` (small JPEG) → 303 → `/result/{id}` 200 with
  dialog markup + `shops_map.js`; `GET /ui-static/js/shops_map.js` 200 `text/javascript`.
- Headless Chromium (CDP, temp script in `data/tmp/`), dialog opened via trigger click, measured after 6 s:

| Viewport | dialog open | scrollWidth ≤ innerWidth | markers | `is-min` | tiles loaded |
|---|---|---|---|---|---|
| 390×844 | yes | 390 = 390 | 6–7 | 1 | 9/9 |
| 1280×800 | yes | yes (1265 incl. scrollbar) | 7–8 | 1 | 9/9 |
| 360×740 | yes | 360 = 360 | 7–8 | 1 | 9/9 |

Geolocation in headless is unavailable → fallback status «Геолокация недоступна — показан центр Москвы.» shown.

## Screenshots (gitignored)

- `agent_docs/reports/web_ui_screens/shops_map_390x844.png`
- `agent_docs/reports/web_ui_screens/shops_map_1280x800.png`
- `agent_docs/reports/web_ui_screens/shops_map_360x740.png`

## Notes

- OSM tile usage policy: `tile.openstreetmap.org` is acceptable for a low-traffic demo only (attribution shown,
  default referrer policy kept). Production requires an own/commercial tile provider and real shop data (API).
- Contract `agent_docs/contracts/web_ui.md` §3/§6 («no external CDN / hosts») needs an explicit exception for the
  demo map — to be recorded by @Planner (agents do not edit contracts).
- Geolocation needs a secure context (HTTPS or localhost); over plain `http://<lan-ip>` the fallback centre is used.
