# Wine repository / catalog data API (Stage 1)

**Status:** approved. Implement as SQLAlchemy (+ pgvector) repository/service under `src/db/` (or `src/core/db/`). HTTP routers optional later; Stage 1 needs callable Python API + tests.

## Entities

Use schema in [wines_schema.md](wines_schema.md). Domain record for reads may join lookup names (`category_name`, `region_name`, `sweetness_name`).

## Operations

### CRUD by id

- `create(wine_fields) -> Wine`
- `get_by_id(id) -> Wine | None`
- `update(id, fields) -> Wine | None`
- `delete(id) -> bool` — **hard** delete
- `list(*, limit, offset) -> list[Wine]`

### Slug

- `get_by_slug(slug) -> Wine | None`
- `upsert_by_slug(slug, fields) -> Wine` — import path; updates `modified_at`

### Batch

- `get_many_by_ids(ids: Sequence[int]) -> list[Wine]` — order may follow input ids or stable id order (document choice)

### Vector top-K

```python
def search_by_embedding(
    embedding: Sequence[float],
    *,
    top_k: int = 5,
) -> list[RankedHit]:
    ...
```

- Input embedding already computed (YOLO/DINO **outside** this method).
- Default `top_k=5` (TZ).
- Return shape aligned with [retrieval.md](retrieval.md) (`wine_id`, `slug`, `score`, `title`, `manufacturer`, `category`, `image_path` / `image_url`).
- Score: higher = better; document distance→score mapping (e.g. cosine similarity).

**Out of scope v1:** combine vector ORDER BY with attribute filters in one SQL.

### Attribute filters

```python
def search_filters(
    *,
    category_name: str | None = None,      # color: Белое / …
    sweetness_name: str | None = None,     # сухое / брют / …
    region_name: str | None = None,
    manufacturer: str | None = None,       # exact match preferred; ILIKE allowed if documented
    grape_substring: str | None = None,    # ILIKE %…% on grape_variety
    dish: str | None = None,               # dish ∈ dishes array
    rating_min: float | None = None,
    rating_max: float | None = None,
    alcohol_min: float | None = None,
    alcohol_max: float | None = None,
    sort_by_rating: Literal["asc", "desc"] | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Wine]:
    ...
```

All criteria AND. Omit unset filters. No `title ILIKE` in Stage 1 (fuzzy/OCR is separate).

## Not in this contract

- Full-text search, soft-delete, facets, GraphQL.
