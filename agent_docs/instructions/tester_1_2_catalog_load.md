# @Tester — Stage 1.2 Catalog load verification

**After:** @Coder finishes [`coder_1_2_catalog_load.md`](coder_1_2_catalog_load.md).  
**Contracts:** [`../contracts/catalog_prepare.md`](../contracts/catalog_prepare.md), [`../contracts/wines_schema.md`](../contracts/wines_schema.md)

## Goal

Verify prepare artifacts and that the **imported** DB matches expectations (table presence + counts + a couple of repository reads). **Not** retrieval accuracy.

## Setup

Follow quickstart from manuals (compose, `.env`, alembic, prepare, import) as implemented by @Coder.

## Checks

### Files

- [ ] `scripts/catalog_prepare/wines_ready.csv` exists, non-empty (no fixed row count — catalog size changes)
- [ ] `wines_additional.csv` exists, non-empty
- [ ] `wines_rejected.csv` exists with `reason` column
- [ ] Enrich columns present on all three (rating / alcohol / dishes / temperature as applicable)

### SQL / DB

Against Compose DB (`DATABASE_URL` from `.env.example` pattern):

- [ ] Tables `categories`, `regions`, `sweetness_levels`, `wines` exist  
- [ ] `sweetness_levels` has 6 seed names (or ≥6 after import get-or-create)  
- [ ] `wines` count ≈ ready + additional imported (document actual number)  
- [ ] `COUNT(*) FILTER (WHERE embedding IS NULL)` = 0 for imported set  
- [ ] `COUNT(*) FILTER (WHERE image_url IS NULL OR image_url = '')` = 0  
- [ ] Spot-check: random slug from ready has file under `static/wines/`  

### Light unit reads

- [ ] `get_by_slug` for one ready and one additional slug  
- [ ] `search_by_embedding` smoke: encode one imported image → top_k returns that slug in top 5 (smoke only; no hit@1 report required)

## Commands

```bash
docker compose ps
uv run alembic current
uv run pytest tests/ -v -k "catalog_load or import"   # if such tests exist
# plus any SQL script @Coder documented
```

## Out of scope

- owner_eval / Stage 2 accuracy  
- Filling rejected into DB  

## Report

`agent_docs/reports/test_stage_1_2_catalog_load.md` with counts and commands. Append progress.
