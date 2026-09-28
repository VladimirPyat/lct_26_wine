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

# RESOLVED — PROD-000 color semantics (owner decision 2026-09-28: color = `categories.name`)

Contract `product_api.md` §2 updated: `WineCard.color` = `categories.name`, new `WineCard.shade` = `wines.color`
(display only); `CatalogFilters.category` / `Dictionaries.categories` removed (duplicated color).
Original question kept below for history.

## Original question

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

# OPEN — PROD-API vector analogs when OCR rerank switched the winner

**Date:** 2026-09-28  
**Role:** @Tester (tester_product_api, report `test_product_api.md` DEF-1)

## Issue

`product_api.md` §4.2 defines `vector` analogs as «candidates rank 2..K as cards». This assumes the
winner is candidate rank 1. When OCR rerank switches the winner (`decision.slug` = candidate rank ≥ 2,
typical in low-margin → `status=low` cases), `CatalogProductService._vector_analogs` still returns
ranks 2..K, so the **winner itself is shown as its own analog**, and the image top-1 (not the winner)
is dropped. `ocr_filters` / `winner_filters` do exclude the winner (`exclude_slugs=[winner]`).

Repro: `tests/test_product_api.py::test_search_low_rerank_switch_vector_excludes_winner` (FAILS).

## Decision needed (Planner)

Confirm the intended rule: «all candidates except the winner» (test expectation) vs literal
«ranks 2..K». Implementation change is @Coder scope; the test stays as written until decided.
