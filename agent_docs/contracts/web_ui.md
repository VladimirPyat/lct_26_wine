# Contract — Web UI (Jinja2, Stage 4)

**Scope:** server-rendered public UI in `src/web/` (rules: `frontend-coding.mdc`, `frontend-linting.mdc`, `frontend-testing.mdc`).  
**Data:** only via `request.app.state.product_service` (`ProductService`, [`product_api.md`](product_api.md) §3). No DB / pipeline imports in `src/web/`; no HTTP calls to our own `/api/v1`.  
**Design reference:** [`../reports/frontend_design_review.md`](../reports/frontend_design_review.md) (§2 what to take, §4.7 responsive), screenshots/prototype in `agent_docs/drafts/front_migration/web/` (visual only — do not copy code).

---

## 1. Layout

```
src/web/
  __init__.py
  router.py            # APIRouter (no prefix) — pages below
  views.py             # view models (dataclasses) built from DTOs
  templating.py        # Jinja2Templates(autoescape, StrictUndefined in tests/dev), filters (rating, confidence label)
  templates/
    base.html          # <head>, header nav (desktop), bottom tab bar (mobile), flash/toast slot
    components/        # wine_card.html, candidate_strip.html, analogs.html, filters.html, confidence_badge.html, feedback.html, stub_feature.html
    pages/             # scan.html, result.html, wine.html, catalog.html, me.html, error.html
  static/
    css/tokens.css     # brand tokens (colors, radius, spacing, font stack)
    css/app.css        # mobile-first + desktop media queries
    js/camera.js       # getUserMedia + aim overlay + snap full frame
    js/upload.js       # drag&drop + file input → POST /search
    js/store.js        # localStorage "cabinet"
    js/lightbox.js
    img/               # logo, glass icons (copied from prototype assets: znak.png, glass_*.png, rating svgs)
```

Mount in `src/api/main.py`: `app.include_router(web_router)` and `app.mount("/ui-static", StaticFiles(directory=src/web/static), name="ui_static")`. Catalog images stay at `/static/wines/`.

## 2. Pages

| Route | Method | Behaviour |
|---|---|---|
| `/` | GET | Scanner page: camera viewport with aim frame (corners) + snap button; «Загрузить фото» (file input, `accept="image/*"`); desktop: webcam if available **and** drag&drop zone. Works without JS as a plain `<form method=post enctype=multipart/form-data action=/search>` |
| `/search` | POST | Validate upload (size/type from service-side settings; on reject → re-render `/` with error, HTTP 400/413/415) → `service.search(tmp, original_name=…)` → **303** to `/result/{search_id}` |
| `/result/{search_id}` | GET | 404 page if unknown. Renders by `status` (§3). `?analogs=1` on `found` → calls `service.analogs_for` and shows analogs block |
| `/result/{search_id}/photo` | GET | `FileResponse(service.query_photo_path(id))` or 404; `Cache-Control: private` |
| `/result/{search_id}/feedback` | POST | form `verdict=match|mismatch`, optional `slug` → `service.record_feedback` → 303 back to result with `?fb=1` (thank-you state); `mismatch` also shows «Подобрать аналоги» |
| `/wine/{slug}` | GET | Wine card page (from history/favorites/analogs/catalog); 404 if unknown |
| `/catalog` | GET | Query params = `CatalogFilters` fields + `page`; filter form from `service.dictionaries()`; results `service.find_wines(limit=20)` sorted by rating |
| `/me` | GET | Server renders shell; JS fills from localStorage (§5). Not logged in → «Войти» button |

All user-facing text in Russian. Unknown errors → `error.html` (no stack traces).

## 3. Result states

| `status` / level | Must show |
|---|---|
| `found` (`high` / `medium`) | Wine card (image, manufacturer, title, tags color/category/region, grape, description, `public_rating` as glasses or «нет оценок», dishes chips), confidence badge «Высокая / Средняя уверенность», **«Открыть на сайте»** (`product_url`; hidden if null), **feedback «Это то вино? Да / Нет»**, «Подобрать аналоги» button (no auto analogs), «Исходное фото» (lightbox from `/result/{id}/photo`), favorite toggle |
| `low` | Same card + badge «Низкая уверенность — возможно, это не то вино» + analogs block shown immediately + feedback |
| `not_found` | Message «Вино не найдено в каталоге. Воспользуйтесь подбором аналогов» + analogs block (filters chips from OCR hints, cards) + link «Уточнить в каталоге» (`/catalog?…` with the same filters). No winner card |
| analogs block | Title by `source` (`ocr_filters`: «Похожие по этикетке», `winner_filters`: «Аналоги от других виноделен», `vector`: «Похожие по виду»); applied filters as chips linking to `/catalog` with that filter removed; ≤5 cards; «Показать все (N)» → `/catalog` if `total > 5`; empty → «Ничего похожего не нашли» + link to catalog |

Confidence is shown **only as a text level**, never as percent / raw cosine. `candidates` are not shown in UI (API only).

Stubs (visible, disabled or toast «Скоро»): «Цифровой сомелье» (dish chips Мясо/Рыба/Сыры may prefill `/catalog?dish=`), «Найти в магазинах рядом», «Чат».

## 4. Responsive (from design review §4.7)

| | Phone (< 768px) | Desktop (≥ 1024px) |
|---|---|---|
| Nav | Bottom tab bar, app style, fixed, safe-area inset: Сканер · Каталог · Мои вина (scanner centered, emphasized) | Header: logo left, links right; no tab bar |
| Scanner | Full-width camera, controls in thumb zone | Two columns: webcam (if available) + drop zone / tips + recent searches |
| Result | Photo above info; sticky bottom action bar (Да/Нет, «На сайте») above tab bar | Photo left, info + actions right; analogs grid 3–4 per row |
| Catalog | Filters in slide-over panel | Filters sidebar left, grid right |

768–1023px: phone layout with 2-column grids. Requirements: no horizontal scroll at 360px; zoom allowed (no `user-scalable=no`); touch targets ≥ 44px; both orientations; images `object-fit`, `loading="lazy"` for grids; brand tokens from prototype (bordeaux accent, light background, rounded cards); system font stack or self-hosted font (no Google Fonts CDN).

## 5. Browser «cabinet» (`js/store.js`)

- localStorage key prefix `svoe_vino:v1:`; all reads tolerant to corrupt JSON (reset key).
- `auth`: `{logged_in: bool}` — «Войти» sets true (no credentials), «Выйти» sets false (data kept).
- `history`: last 50 `{ts, search_id, slug|null, title|null, status, level}` — written on result page load (data from `data-*` attributes rendered by server); **no photos**.
- `favorites`: `slug[]`; `ratings`: `{slug: 1..5}` (my rating, never mixed with `public_rating`); `feedback`: `{search_id: verdict}`.
- `/me`: tabs История / Избранное / Мои оценки; each item links to `/result/{id}` or `/wine/{slug}`; «Очистить мои данные».
- Cabinet features visible only when `logged_in` (history is still recorded).

## 6. JS rules

- Progressive enhancement: every flow works via plain forms; JS adds camera, drag&drop, lightbox, cabinet.
- `camera.js`: `getUserMedia({video:{facingMode:"environment"}})`; aim overlay is **visual only**; snap draws the **full frame** to canvas → JPEG → `FormData(image)` → `fetch("/search", {method:"POST"})` → `location = response.url` (after 303). Camera unavailable / not secure context → hide camera, keep upload (message: камера требует HTTPS).
- No client-side detection / cropping / ONNX. No external CDNs.
- Errors from fetch → inline message, never `alert` only, never swallowed.

## 7. Security

- Autoescape on; no `|safe` on catalog / OCR / user data; `product_url` rendered only if `http(s)://` (else hidden), `rel="noopener noreferrer" target="_blank"`.
- `search_id` path params validated as 32-hex before calling the service.
- Upload limits enforced server-side from `request.app.state.product_settings.upload` (same settings as API).
