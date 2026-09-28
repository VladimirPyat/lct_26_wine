# BLOCKED — Stage 2B

**Date:** 2026-09-24  
**Role:** @Coder (coder_2b_eval) → **RESOLVED** (user approved `phocr` + numpy override)

## Issue (resolved)

Package `phocr` was missing from `ml` extras. Metadata pins `numpy<=1.26.4` while the project needs numpy 2.x.

## Resolution

User approved install. Applied (same pattern as prior vine repo):

- `phocr>=1.0.3` under `[project.optional-dependencies] ml`
- `[tool.uv] override-dependencies = ["numpy>=2.0.0"]`
- `uv sync --extra ml --extra db --extra dev` → import OK

## Status

Unblocked for `ocr.engine=phocr` + `enable_rerank=true`. Proceed with @Tester `tester_2b_eval.md`.

---

# OPEN QUESTION — PROD-000 (non-blocking for PROD-000, needs Planner before PROD-API)

**Date:** 2026-09-28  
**Role:** @Coder (coder_prod_000_shared)

## Issue

`product_api.md` uses `color` as the wine color («Красное», `OcrHints.color`, `CatalogFilters.color`,
`product.yaml` `analogs.color_synonyms` keys). In the DB the values differ:

- `wines.color` = shade text (`Тёмно-рубиновый`, `Светло-соломенный`, … — hundreds of distinct values);
- `categories.name` = `Красное` / `Белое` / `Розовое` / `Оранжевое` (what the contract calls color).

So filtering `wines.color = 'Красное'` returns nothing, and `Dictionaries.colors` built from
`wines.color` would be a list of shades.

## What PROD-000 did

- DTOs / `product.yaml` kept verbatim per contract (no schema change).
- `StubProductService` fixtures use real DB values (`color` = shade, `category` = «Красное»…);
  stub analogs filter by `grape` only (+ exclusions); the color hint is shown in `OcrHints`.

## Decision needed (Planner / owner)

Map contract «color» to `categories.name` (and keep `wines.color` as display-only shade), or keep
`color` = `wines.color` and filter by `category` in analogs. Affects `CatalogProductService`
filters, `Dictionaries.colors`, and UI filter labels.
