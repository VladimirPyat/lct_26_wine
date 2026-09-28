# @Coder — WEB-UI: Jinja2 public interface on `ProductService`

**Branch:** `feat/web-ui` (worktree `../lct_vine_web`, port 8082). Starts from `master` with PROD-000 (stub service).  
**Plan:** [`../plans/web_product.md`](../plans/web_product.md) · **Contract:** [`../contracts/web_ui.md`](../contracts/web_ui.md) (+ DTOs in [`../contracts/product_api.md`](../contracts/product_api.md) §2–3)  
**Design reference:** [`../reports/frontend_design_review.md`](../reports/frontend_design_review.md), prototype `agent_docs/drafts/front_migration/web/` (visual reference; assets `znak.png`, `img/glass_*.png`, `svg/public-rating*.svg` may be copied into `src/web/static/img/`).  
**Do not touch:** `src/core/`, `src/db/`, `src/api/routers/`, `config/`, the stub line in `main.py`. Need a DTO change → `BLOCKED.md`.

## Prerequisite

- User ✅ for `uv add jinja2` (recorded in progress). No other dependencies (no htmx/Tailwind/CDN).

## Steps

### WEB-001 — Skeleton

- `src/web/` layout per contract §1; `templating.py` with autoescape, `StrictUndefined` when env `VINE_WEB_STRICT=1` (tests), filters: `confidence_label`, `rating_glasses`, `is_http_url`.
- `main.py`: `include_router(web_router)` + mount `/ui-static`. Nothing else.
- `base.html`: header nav (desktop), bottom tab bar (mobile), `<meta name=viewport content="width=device-width, initial-scale=1">`, CSS tokens.

### WEB-002 — Scanner + upload

- `/` page, no-JS form → `POST /search`; server-side upload validation from `app.state.product_settings.upload`; temp file under `data/tmp/uploads`, deleted after `service.search`; 303 → `/result/{id}`.
- `camera.js` (full frame, aim overlay only), `upload.js` (drag&drop on desktop). Webcam on desktop when available.

### WEB-003 — Result, wine, feedback, analogs

- `/result/{id}` all states (contract §3), `?analogs=1`, `/result/{id}/photo`, `/result/{id}/feedback` (PRG, thank-you state), `/wine/{slug}`.
- Components: `wine_card`, `confidence_badge`, `analogs`, `feedback`, `stub_feature`.
- `lightbox.js` for original photo / bottle image.

### WEB-004 — Catalog

- `/catalog` with filter form from `dictionaries()`, chips for active filters, pagination (`limit=20`, `offset`), empty state.

### WEB-005 — Browser cabinet

- `store.js` + `/me` per contract §5 (login button, history, favorites, my ratings, clear data). History written from `data-*` on result page.

### WEB-006 — Responsive + polish

- Contract §4 breakpoints; check 360×740, 390×844, 768×1024, 1280×800, 1920×1080 (screenshots into `agent_docs/reports/web_ui_screens/` — gitignored binaries per `.gitignore` rules, list them in the report).
- Brand look from prototype (bordeaux accent, rounded cards, glass icons), system font stack.

### WEB-007 — Docs (Russian)

`manuals/quickstart.md` (open `http://127.0.0.1:8080/`, HTTPS note for phone camera), `manuals/architecture.md` (UI layer, stub vs real service), `manuals/manual_testing.md` stub checklist for @Tester (phone camera, orientation).

## Verification

```bash
uv run ruff check src/web/
uv run mypy src/web/ --ignore-missing-imports
uv run pytest tests/ -v
uv run uvicorn api.main:app --app-dir src --port 8082   # stub: upload files named *_low.jpg / *_notfound.jpg to see states
```

## Acceptance

- [ ] All pages and states of contract §2–3 render on the stub; no-JS path works end to end
- [ ] Mobile tab bar / desktop header; no horizontal scroll at 360px
- [ ] Feedback, analogs button, «Открыть на сайте», original photo, favorites, cabinet
- [ ] No `|safe` on data, no inline handlers, no CDN; `product_url` sanitized
- [ ] Only `app.state.product_service` used for data
- [ ] Lint clean; manuals updated

Handoff: `READY_FOR_TEST (WEB-UI)` in `agent_docs/progress/stage_3.md` → @Tester `tester_web_ui.md`.
