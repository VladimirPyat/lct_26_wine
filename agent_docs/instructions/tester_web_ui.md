# @Tester — WEB-UI

**After:** `READY_FOR_TEST (WEB-UI)` · **Branch:** `feat/web-ui` (A–D on stub); §E on `master` after both branches merged.  
**Contract:** [`../contracts/web_ui.md`](../contracts/web_ui.md) · Rules: `frontend-testing.mdc`

Use `TestClient(app)` with `app.state.product_service = StubProductService()` (or a local fake implementing `ProductService`), env `VINE_WEB_STRICT=1`. Do not load models/DB for A–D (patch lifespan / build a test app including `web_router`).

## A. Pages render (`tests/web/test_pages.py`)

- [ ] `GET /`, `/catalog`, `/me`, `/wine/{fixture}` → 200, `text/html`, viewport meta present, no `user-scalable=no`.
- [ ] unknown `/wine/x`, `/result/<32 hex unknown>` → 404 page (HTML, no traceback); `/result/not-hex` → 404 without calling the service.

## B. Search flow (`tests/web/test_search_flow.py`)

- [ ] `POST /search` jpg → 303 `Location: /result/{id}`; follow → found state: wine title, confidence text («Высокая уверенность»), «Открыть на сайте» link, «Это то вино?» form, «Подобрать аналоги» button, **no** analogs block.
- [ ] file named `*_low.jpg` → low badge + analogs block; `*_notfound.jpg` → «не найдено» text + analogs + link to `/catalog?...`, no winner card.
- [ ] `?analogs=1` on found → analogs block with «Аналоги от других виноделен» (stub source permitting).
- [ ] no file → 400 re-render with error; oversized (> max_mb) → 413; `text/plain` → 415.
- [ ] `POST /result/{id}/feedback verdict=match` → 303, stub recorded it; thank-you state shown; `mismatch` shows analogs button.
- [ ] `/result/{id}/photo` → 200 image; unknown → 404.
- [ ] no raw cosine / percent shown in HTML (`score` values of stub absent).

## C. Catalog + analogs

- [ ] filters from query params reflected as chips; chip link removes exactly that filter; pagination links; empty state text.
- [ ] analogs show ≤5 cards and «Показать все (N)» when `total > 5`.

## D. Security / quality

- [ ] stub wine with title `<script>alert(1)</script>` is escaped in `/wine/{slug}` and result.
- [ ] `product_url = "javascript:alert(1)"` → link not rendered.
- [ ] templates: grep test — no `|safe` in `src/web/templates/`, no ` on[a-z]+=` attributes, no `http(s)://` CDN links.
- [ ] static assets referenced in templates exist (`/ui-static/...` → 200).

## E. Integration (on `master` after merge of `feat/product-api` + `feat/web-ui`, HITL)

- [ ] App with real `CatalogProductService`: upload 5 owner_eval photos via `/` → result pages show correct wines (compare with `predictions.jsonl`).
- [ ] feedback line appears in `data/tmp/search_feedback.jsonl`; photo + json in `data/tmp/search_queries/`.
- [ ] owner_eval via `/v1/eval/predict` still 51/52.
- [ ] manual (`manuals/manual_testing.md`): phone camera over HTTPS tunnel, portrait/landscape, desktop webcam, tab bar, cabinet persistence after reload; screenshots listed in report.

## Commands

```bash
uv run ruff check src/web/ tests/web/
uv run pytest tests/web/ -v
```

Report `agent_docs/reports/test_web_ui.md`; append `TEST_PASS` / `TEST_FAIL (WEB-UI)` to `agent_docs/progress/stage_3.md`.
