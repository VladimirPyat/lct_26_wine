# @Coder — Stage 1.2 Catalog prepare + full import

**Depends on:** [`coder_1_0_schema.md`](coder_1_0_schema.md), [`coder_1_1_crud.md`](coder_1_1_crud.md)  
**Contracts:** [`../contracts/catalog_prepare.md`](../contracts/catalog_prepare.md), [`../contracts/wines_schema.md`](../contracts/wines_schema.md)  
**Tester:** [`tester_1_2_catalog_load.md`](tester_1_2_catalog_load.md)

## Goal

1. Scripts that produce `wines_ready.csv`, `wines_additional.csv`, `wines_rejected.csv` (+ JSON enrich on all three).  
2. Import **ready + additional** into Compose Postgres with images in `static/wines/` and DINO embeddings (YOLO optional; catalog shots may encode as-is).  
3. Document how to bring the catalog up.

## Dependencies (approved)

```bash
uv sync --extra ml --extra db --extra dev
uv add pillow
```

(If Pillow better lives in an `extra`, document it; do not use pip.)

## Steps

### A. Prepare scripts — `scripts/catalog_prepare/`

1. Copy `data/owner_database/wines_problem_images.csv` into this folder for audit.
2. `audit_image_sizes.py` (or combined tool): measure owner images; print/write threshold summary.
3. `prepare_ready_csv.py` implementing [catalog_prepare.md](../contracts/catalog_prepare.md):
   - `MIN_SIDE=200`
   - ready / additional / rejected rules (shared photo name → reject whole group; additional = site rescue for small owner + unique content hash)
   - JSON enrich on **all three** outputs (not sweetness column)
4. Do not modify SSOT CSV/JSON under `data/`.

### B. Runtime DB + import

1. Document: `cp .env.example .env` (no secrets required for local vine/vine).
2. `docker compose up -d` → wait healthy → `uv run alembic upgrade head`.
3. Import CLI (e.g. `scripts/catalog_import.py` or `python -m db.import_catalog`):
   - Read ready + additional
   - Resolve category/region get-or-create; map empty text → `н/д`
   - Resolve `sweetness_id` from site JSON `category` via case-insensitive **exact token** match (longest first); else NULL
   - Copy/convert image → `static/wines/{slug}.webp` (or keep ext); set `image_url=/static/wines/...`
   - Encode with DINO; skip row on missing image / encode failure (log)
   - `upsert_by_slug`
4. Create `static/wines/.gitkeep` if needed. Binaries gitignored via `.gitignore`.
5. Optional: build vector index after load (HNSW/IVFFlat) — document; can be follow-up if slow.

### C. Docs (required)

- [`manuals/quickstart.md`](../../manuals/quickstart.md): compose → .env → alembic → prepare → import → verify counts  
- [`manuals/configuration_guide.md`](../../manuals/configuration_guide.md): paths to owner/site data, `MIN_SIDE`, static dir, import flags  
- [`manuals/architecture.md`](../../manuals/architecture.md): prepare → import → encode → pgvector data flow  
- Sync [`manuals/index.md`](../../manuals/index.md)  
- README link check if quickstart entrypoints changed  

## Out of scope

- Search accuracy / owner_eval harness (Stage 2)
- Importing `wines_rejected` into DB (files remain for later)
- Frontend StaticFiles mount can be minimal stub or deferred if import-only verification uses filesystem + SQL — prefer mounting `/static` on FastAPI for later UI; note in quickstart

## Acceptance

- [ ] Three CSVs generated under `scripts/catalog_prepare/` with enrich columns
- [ ] Import loads ready+additional; `static/wines/` populated for imported slugs
- [ ] Every imported row has non-null embedding and image_url
- [ ] Manuals/quickstart describe the full path
- [ ] Lint gate on changed Python

## Handoff

Append `READY_FOR_TEST` (catalog load) to `agent_docs/progress/stage_1.md` → @Tester [`tester_1_2_catalog_load.md`](tester_1_2_catalog_load.md).
