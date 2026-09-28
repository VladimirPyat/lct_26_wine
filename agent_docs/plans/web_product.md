# Plan — Product API + Web UI in parallel branches (Stage 3 + 4)

**Opened:** 2026-09-28 · **Owner decisions:** [`../reports/frontend_design_review.md`](../reports/frontend_design_review.md) §3 · **TZ gaps:** [`../reports/ticket_tz_gap_001_remaining_scope.md`](../reports/ticket_tz_gap_001_remaining_scope.md)  
**Contracts:** [`../contracts/product_api.md`](../contracts/product_api.md), [`../contracts/web_ui.md`](../contracts/web_ui.md)

## Locked decisions

- One FastAPI app; UI = Jinja2 in `src/web/`, same process as the backend (no separate UI service).
- UI and JSON API both call `ProductService` (in-process). UI branch develops against `StubProductService`; the real service arrives with the backend branch.
- `/v1/eval/predict` unchanged (organizer harness).
- Feedback → JSONL log (not DB). Query photos → `data/tmp/search_queries/`, 10-day retention.
- Confidence = text level from image cosine; thresholds are placeholders until calibration (not a UI concern).
- Analogs (owner 2026-09-28, supersedes OCR-color / vector chain): same grape only, ≤5 by `public_rating`. `found` → on button, winner's grape from DB, no OCR, «from other wineries»; `low` / `not_found` → OCR grape only (Latin names mapped); no grape / 0 matches → empty («аналог подобрать не удалось»). `vector` not produced.
- OCR engine chain (owner 2026-09-28): CUDA → PHOCR; no CUDA → LLM OCR; no LLM → no OCR (rerank skipped).

**Status (2026-09-28):** PROD-API implemented + tested (DEF-1 obsolete); follow-up [`coder_product_api_fix1.md`](../instructions/coder_product_api_fix1.md) → [`tester_product_api_fix1.md`](../instructions/tester_product_api_fix1.md) INSTRUCTIONS_READY. UI impact for the merge with `feat/web-ui` — `product_api.md` §4.2 «UI impact».
- Browser-only cabinet (localStorage), demo «Войти» button; sommelier / map / chat = stubs.

## Order

| Step | Where | Instruction | Result |
|---|---|---|---|
| 0 | `master` (after `feat/siglip-prod` merge) | [`coder_prod_000_shared.md`](../instructions/coder_prod_000_shared.md) | DTOs + `ProductService` Protocol + stub + `product.yaml` loader committed on `master` |
| 1a | `feat/product-api` (worktree A) | [`coder_product_api.md`](../instructions/coder_product_api.md) → [`tester_product_api.md`](../instructions/tester_product_api.md) | `CatalogProductService`, `/api/v1/*`, analogs, dictionaries, storage, feedback, calibration script |
| 1b | `feat/web-ui` (worktree B) | [`coder_web_ui.md`](../instructions/coder_web_ui.md) → [`tester_web_ui.md`](../instructions/tester_web_ui.md) | `src/web/` pages on stub |
| 2 | merge 1a and 1b into `master` (any order) | — | expected conflict only in `src/api/main.py` router/mount lines and `manuals/` — keep both |
| 3 | `master` | `tester_web_ui.md` §E (integration) | UI on real service; owner_eval regression unchanged |

## Worktrees (human runs, after step 0)

```bash
cd /work/lct_vine_final
git worktree add ../lct_vine_api -b feat/product-api master
git worktree add ../lct_vine_web -b feat/web-ui master
# symlinks are files for git ("data/" pattern matches dirs only) → exclude them for all worktrees
printf '/data\n/bin\n' >> .git/info/exclude
# untracked assets each worktree needs
for d in ../lct_vine_api ../lct_vine_web; do
  cp -r .cursor "$d/"                              # rules/hooks are not in git
  ln -s "$PWD/bin" "$d/bin"
  ln -s "$PWD/data" "$d/data"
  cp -al "$PWD/static/wines/." "$d/static/wines/"  # hard links; static/wines/.gitkeep is tracked
  cp .env "$d/.env"
done
```

- Open each worktree as a **separate Cursor window**; one agent per window.
- One Postgres (`docker compose up -d` only from the main folder). API ports: main 8080, api-worktree 8081, web-worktree 8082.
- `data/` is shared via symlink: both branches write only their own subpaths (`data/tmp/search_queries/`, `data/tmp/search_feedback.jsonl` — backend; UI stub writes nothing to disk).
- Remove later: `git worktree remove ../lct_vine_api` (after merge).

## Preconditions

- `.cursor/rules/` contains the Jinja drafts from `agent_docs/drafts/cursor_rules/` (paths-access with `src/web/`, `tests/web/`, `data/tmp/search_queries/`; tooling with Frontend section).
- User ✅ for `uv add jinja2` (web branch only).

## Out of scope

Admin panel, sommelier/LLM chat, maps/shops, real auth, DB table for feedback, dedupe of catalog SKUs (DATA-DEDUP-001), Docker for API / one-command private run (TZ-GAP items 5–6 — next plan).
