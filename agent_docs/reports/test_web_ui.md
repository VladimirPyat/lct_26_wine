# Test report — WEB-UI (sections A–D)

**Date:** 2026-09-28 · **Branch:** `feat/web-ui` (worktree `.worktrees/web`) · **Tested commits:** `f01b5eb..bd4aaf3`  
**Instruction:** `agent_docs/instructions/tester_web_ui.md` §A–D · **Contract:** `agent_docs/contracts/web_ui.md`  
**Verdict:** **TEST_PASS (WEB-UI A–D)** — all checklist items green; 1 minor contract gap recorded as strict `xfail` (BUG-WEB-01) for @BugFixer. §E pending (runs on `master` after merge).

## Setup

- Test app per test: `FastAPI()` + `web_router` + `/ui-static` `StaticFiles` mount, `app.state.product_service = StubProductService()` (or a local fake), `app.state.product_settings = load_product_settings()`. Real lifespan / models / DB are **not** loaded.
- `VINE_WEB_STRICT=1` is set in `tests/web/conftest.py` before importing `web`; an autouse fixture also sets `templates.env.undefined = StrictUndefined`, because in the full suite `web` is imported earlier (via `api.main` in `tests/test_eval_predict_api.py`) and the Jinja env is built at import time (see note N-2).
- Fakes (`tests/web/web_helpers.py`): `FixtureStub` (stub with custom wine list — XSS strings, 8/45 red wines for caps/pagination, whites for empty analogs / vector source), `SpyService` (records calls), plus local subclasses for over-limit analogs and a 500 error.
- HTML checked with stdlib `html.parser` (no new deps). No playwright, no package / lockfile changes.

## Files

| File | Section |
|---|---|
| `tests/web/conftest.py` | fixtures (`stub`, `client`, `make_client`, `product_settings`, strict templates) |
| `tests/web/web_helpers.py` | app builder, fakes, HTML parser, upload helpers |
| `tests/web/test_pages.py` | A |
| `tests/web/test_search_flow.py` | B |
| `tests/web/test_catalog_analogs.py` | C |
| `tests/web/test_security.py` | D |

No `tests/web/__init__.py` on purpose: with it, pytest would import the test package as `web` and shadow `src/web`.

## Checklist

### A. Pages render — 14 passed

- [x] `GET /`, `/catalog`, `/me`, `/wine/{fixture}` → 200, `text/html`, single viewport meta with `width=device-width`, no `user-scalable` / `maximum-scale=1`; `<html lang="ru">`. Scanner has a no-JS `<form method=post enctype=multipart/form-data action=/search>` with `input[type=file][name=image]`; nav links `/`, `/catalog`, `/me`.
- [x] unknown `/wine/x` and `/result/<32 hex unknown>` → 404 HTML page, no traceback.
- [x] `/result/not-hex` (also uppercase hex, 16 chars, `z`×32) → 404 for page, `/photo` and `POST /feedback`; `SpyService.calls == []` (service never called).

### B. Search flow — 32 passed

- [x] `POST /search` jpg → 303 `Location: /result/{32hex}`; temp upload cleaned. Follow → found: title, «Высокая уверенность», «Открыть на сайте» (`target=_blank`, `rel=noopener noreferrer`), «Это то вино?» form (POST, `verdict=match|mismatch`), «Подобрать аналоги» → `?analogs=1`, «Исходное фото» → `/photo`, **no** analogs block; other candidates' titles absent (candidates are API-only).
- [x] `*_low.jpg` → «Низкая уверенность — возможно, это не то вино» + analogs block «Похожие по этикетке» + feedback. `*_notfound.jpg` → «Вино не найдено в каталоге. Воспользуйтесь подбором аналогов» + analogs + «Уточнить в каталоге» `/catalog?color=…&grape=…`; no badge, no winner card.
- [x] `?analogs=1` on found → «Аналоги от других виноделен» with the stub analog; button hidden; `?analogs=0` → no block.
- [x] no file (no multipart / wrong field) → 400 scanner re-render with visible error; empty file → 400; > `max_mb` → 413 (both with patched `max_mb=0.001` in `app.state.product_settings` and the real 15 MB config); exactly `max_bytes` → 303; `text/plain` → 415; GIF → 415; declared JPEG with garbage bytes → 400 (documented deviation); PNG → 303. Service not called on rejects; no temp files left.
- [x] `POST /result/{id}/feedback verdict=match` → 303 `/result/{id}?fb=1&verdict=match#feedback`; stub recorded `{search_id, slug=winner, verdict=match}`; slug omitted → server fills winner slug; thank-you state, form gone. `mismatch` → thank-you + «Подобрать аналоги». Invalid verdict (`""`, `maybe`, `MATCH`) → 400, nothing recorded; unknown id → 404.
- [x] `/result/{id}/photo` → 200 `image/*`, `Cache-Control: private…`, same bytes; unknown → 404.
- [x] no raw scores: `score_1`, `margin`, all candidate scores absent as decimals (`0.91`, `0,91`) in HTML and as percent (`91%`) in visible text — for found, found+analogs, low, not_found; no `score` / `cosine` words.

### C. Catalog + analogs — 16 passed, 1 xfailed

- [x] `?color=Красное&region=Кубань` → 2 chips, each link removes exactly its filter; «Сбросить все»; «Найдено: 2»; only the 2 matching wines. All 7 filter kinds (incl. `exclude_manufacturer` «Кроме винодельни: …», `exclude_slugs` «Без найденного вина») → one chip each; removing one keeps all others. `<select>` preselects query values. Sorted by rating (unrated last).
- [x] pagination (45 wines / 20): page 1 → 20 tiles, links to pages 2 and 3 carrying the filters, `rel=next` → page 2, no prev, current page `aria-current`; page 2 → disjoint 20 tiles, prev → URL without `page`, next → 3; page 3 → 5 tiles, no next. `page=abc|-1|0|99999999` → 200 with results.
- [x] empty state: «По этим фильтрам вин не нашлось.» + «Сбросить фильтры»; chip still shown.
- [x] analogs: low search with 8 red wines → 5 tiles + «Показать все (7)» → `/catalog?color=Красное&grape=Каберне+Совиньон&exclude_slugs=red-00`; `?analogs=1` on found → 5 tiles + «Показать все (7)», `analogs_for` called. total ≤ 5 → no «Показать все». Analog chips remove one filter. Empty analogs → «Ничего похожего не нашли» + catalog link. `vector` source → «Похожие по виду».
- [ ] **xfail (strict) — BUG-WEB-01:** service returning 7 wines despite `limit` → UI renders all 7 cards (contract §3: block shows ≤5).

### D. Security / quality — 64 passed

- [x] wine with `<script>alert(1)</script>` / `"><img src=x onerror=…>` in title, manufacturer, region, shade, grapes, dishes, description, serving temperature → escaped in `/wine/{slug}`, result pages (found, `?analogs=1`, mismatch thank-you, low, not_found tiles, `data-*` attributes), catalog tiles, chips and `<select>` (also when the XSS comes from query params); no inline `<script>`, no `on*` attributes after parsing. Malicious upload filename not reflected unescaped.
- [x] `product_url` = `javascript:alert(1)`, ` JavaScript:…`, `data:text/html,…`, `//evil…`, `vino-svoe.ru/…`, `https://` → «Открыть на сайте» not rendered on `/wine` and result; no `javascript:`/`data:text` in href/src/action. Valid https → `target=_blank rel="noopener noreferrer"`; `None` → hidden.
- [x] template grep (13 templates): no `|safe`, no `autoescape false`, no ` on[a-z]+=`, no `http(s)://`; static CSS/JS have no external URLs; `src/web/*.py` has no `Markup(` / `autoescape=False`; env autoescape on; StrictUndefined raises on missing vars.
- [x] static assets: every `url_for('ui_static', path=…)` literal in templates exists and `/ui-static/…` → 200; all `/ui-static/…` URLs from 11 rendered pages/states → 200; JS relative imports and CSS `url()` refs resolve.
- [x] unhandled service exception → `error.html` 500 «Что-то пошло не так…», no trace, no exception text.

### E. Integration — PENDING

Out of scope here; runs on `master` after merging `feat/product-api` + `feat/web-ui` (real `CatalogProductService`, feedback JSONL, owner_eval 51/52, HITL manual checks).

## Commands

| Command | Result |
|---|---|
| `uv run ruff check src/web/ tests/web/` | exit 0 — All checks passed |
| `uv run pytest tests/web/ -v` | exit 0 — **126 passed, 1 xfailed** |
| `uv run pytest tests/ -v -k "not owner_eval"` | exit 0 — **208 passed, 4 deselected, 1 xfailed** (82 pre-existing + 126 web; no regressions) |

(`ruff format tests/web/` was applied to test files only.)

## Bugs

### BUG-WEB-01 (minor) — analogs block not capped at 5 cards

- **Where:** `src/web/views.py` `build_analogs_view` (~l.172–183): `wines=list(analogs.wines)` passes the service list through.
- **Contract:** `web_ui.md` §3 analogs block: «≤5 cards; «Показать все (N)» → /catalog if total > 5».
- **Repro:** `tests/web/test_catalog_analogs.py::test_c2_ui_caps_cards_even_if_service_returns_more` — fake `analogs_for` returns 7 wines, `total=12`; result `?analogs=1` renders 7 tiles.
- **Impact:** low — stub and (expectedly) the real service honour `limit`; the UI relies on it. Fix: slice to `settings.analogs.limit` (or 5) in the view; `show_all_url` condition already uses `total > len(wines)`.
- Test is `xfail(strict=True)` → will turn into XPASS failure once fixed; then remove the marker.

## Notes / observations (not contract violations)

- **N-1 (hardening):** `WineCard.image_url` is rendered unchecked in `href` of the lightbox link (`pages/result.html` l.35, `pages/wine.html` l.11) and in `<img src>` (`components/wine_card.html` `wine_image`). A value like `javascript:alert(1)` would produce a clickable `javascript:` link. Contract §7 only requires the check for `product_url` and `image_url` comes from our own import (`/static/wines/…`), so no test was added; suggest the same `http_url`/relative-path guard for @Coder/@BugFixer.
- **N-2:** `web.templating` reads `VINE_WEB_STRICT` at import time; tests patch `templates.env.undefined` to keep StrictUndefined in the full suite.
- **N-3:** coder deviations accepted as documented: no `candidate_strip.html`, extra `js/ui.js`, extra localStorage key `svoe_vino:v1:titles`, feedback redirect `?fb=1&verdict=<v>#feedback`, magic-byte type check (declared type picks 400 vs 415). Non-web paths returning FastAPI JSON 404 — known, out of scope.
- Responsive / camera / cabinet (localStorage) behaviour is not covered by TestClient; belongs to §E HITL (`manuals/manual_testing.md`).

## Next step

- @BugFixer: BUG-WEB-01 (optional N-1) on `feat/web-ui`; then remove the `xfail` marker and rerun `uv run pytest tests/web/ -v`.
- After merge to `master`: @Tester §E (integration + HITL).
