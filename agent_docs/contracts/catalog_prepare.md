# Catalog prepare CSV (Stage 1)

**Status:** approved. Scripts under `scripts/catalog_prepare/`. Do not rewrite SSOT files under `data/owner_database/` except reading them.

## Inputs (read-only)

| Path | Role |
|------|------|
| `data/owner_database/wines_integrated_updated.csv` | Owner truth (~2103 rows) |
| `data/owner_database/images/` | Local `.webp` (~2037) |
| `data/owner_database/wines_problem_images.csv` | Audit hint; copy into script folder |
| `data/site_database/wines_database_enriched.json` | Enrich by slug |
| `data/site_database/images/` | Site images for additional rescue |

## Constants

- `MIN_SIDE = 200` (min(width, height) via Pillow on disk files)

## Outputs (write under `scripts/catalog_prepare/`)

| File | Rule |
|------|------|
| `wines_problem_images.csv` | Copy of owner problem list (audit) |
| `wines_ready.csv` | Owner image exists; min_side ≥ 200; unique `Файл в wines_images`; unique «Название фото» (shared name → reject **entire** group); `image_source=owner` |
| `wines_additional.csv` | In JSON, not in ready; owner min_side &lt; 200; site `{slug}.webp` min_side ≥ 200; **unique content hash** among additional; `image_source=site`; `source_image` = site filename |
| `wines_rejected.csv` | Remaining owner CSV rows not in ready/additional; include `reason` |
| size audit report (optional CSV) | Per-file width/height/min_side |

### Shared columns (ready / additional; rejected + reason)

`slug`, `title`, `category`, `color`, `region`, `grape_variety`, `description`, `manufacturer`, `source_image`, `product_url`, `image_source`

### JSON enrich (all three CSVs)

Match by `slug`. Do **not** overwrite owner text fields. Add/fill:

- `public_rating`
- `serving_temperature`
- `alcohol_pct` (parse rules as in wines_schema)
- `dishes` (serialize list, e.g. JSON array string in cell)
- `product_url` if empty

**Do not** add `sweetness` columns to these CSVs (resolved at DB import from JSON).

## Import to DB (separate step)

First production load: **ready + additional** only (image + embedding required). Rejected kept for later manual fixes / fallback — not required in first import tests beyond existing as files.
