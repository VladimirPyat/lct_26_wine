# Wines catalog schema (Stage 1)

**Status:** approved (Phase A). Single catalog DB: Postgres + pgvector.

## Extensions

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## Lookup tables

### `categories` (color / type from owner CSV «Категория»)

| Column | Type | Notes |
|--------|------|--------|
| id | BIGSERIAL PK | |
| name | TEXT UNIQUE NOT NULL | e.g. Белое, Красное, Розовое, Оранжевое |

### `regions`

| Column | Type | Notes |
|--------|------|--------|
| id | BIGSERIAL PK | |
| name | TEXT UNIQUE NOT NULL | e.g. Кубань, Крым |

### `sweetness_levels` (site-style dryness; not in owner CSV «Категория»)

| Column | Type | Notes |
|--------|------|--------|
| id | BIGSERIAL PK | |
| name | TEXT UNIQUE NOT NULL | Canonical: `сухое`, `полусухое`, `полусладкое`, `сладкое`, `брют`, `экстра брют` |

Seed these six names on migrate (or get-or-create on first import). Matching from JSON `category` string is **case-insensitive exact token** search (prefer longer token first: `экстра брют` before `брют`). No match → `wines.sweetness_id` NULL.

## `wines`

| Column | Type | Null | Source / notes |
|--------|------|------|----------------|
| id | BIGSERIAL | PK | Auto-increment |
| slug | TEXT | UNIQUE NOT NULL | Owner CSV; skip row if missing |
| title | TEXT | NOT NULL | «Название вина»; skip if missing |
| category_id | BIGINT FK → categories | NOT NULL | CSV «Категория»; empty → sentinel `н/д` |
| color | TEXT | NOT NULL | CSV «Цвет»; empty → `н/д` |
| region_id | BIGINT FK → regions | NOT NULL | CSV «Регион»; empty → `н/д` |
| grape_variety | TEXT | NOT NULL | CSV; empty → `н/д` |
| description | TEXT | NOT NULL | CSV; empty → `н/д` |
| manufacturer | TEXT | NOT NULL | CSV «Винодельня»; empty → `н/д` |
| public_rating | DOUBLE PRECISION | NULL | JSON |
| product_url | TEXT | NULL | CSV page URL, else JSON |
| serving_temperature | TEXT | NULL | JSON `temperature` as-is |
| alcohol_pct | NUMERIC(4,1) | NULL | JSON: single number or **max** of range; if parsed **> 35** → NULL |
| dishes | TEXT[] | NULL | JSON `dishes` list |
| sweetness_id | BIGINT FK → sweetness_levels | NULL | From JSON category tokens only (not in prepare CSV) |
| image_url | TEXT | NOT NULL | Public path e.g. `/static/wines/{slug}.webp` |
| embedding | vector(N) | NOT NULL | Image encoder output, L2-normalized; **N** = `database.yaml` `embedding_dim` = ONNX output dim (SigLIP2 so400m: **1152**; DINOv2-base was 768). Dim change → alembic `0002_embedding_dim` + full reimport |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| modified_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | Bump on UPDATE |

**Insert rule:** no usable image or encode failure → do **not** insert (log skip). Hard DELETE only (no soft-delete).

## Storage

| Asset | Location |
|-------|----------|
| Row + embedding | Postgres Docker volume `pgdata` |
| Catalog images served to UI | `static/wines/` on host (`image_url` = `/static/wines/...`) |
| Source photos (import) | `data/owner_database/images/`, `data/site_database/images/` |

## Indexes (after first full load OK to create)

- UNIQUE(slug)
- HNSW or IVFFlat on `embedding` (cosine or IP — match DINO score convention in retrieval contract)
- Optional BTREE on category_id, region_id, sweetness_id, public_rating, alcohol_pct

## Naming vs OCR types

DB/API English names: `title`, `manufacturer` (match existing `WineRecord` / fuzzy). Map CSV «Винодельня» → `manufacturer`.
