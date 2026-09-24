# @Coder — Stage 1.0 Database schema

**Contracts:** [`../contracts/wines_schema.md`](../contracts/wines_schema.md), [`../drafts/infra_postgres.md`](../drafts/infra_postgres.md)  
**Follow with:** [`coder_1_1_crud.md`](coder_1_1_crud.md) after this is done.

## Goal

Create Alembic + SQLAlchemy models for lookups and `wines` (including `vector(N)`). No full catalog import yet.

## Dependencies (approved)

```bash
uv sync --extra db --extra dev
uv add alembic
```

Add `alembic` to the `db` extra in `pyproject.toml` if that keeps the project consistent (prefer one place).

## Steps

1. Initialize Alembic under `alembic/` targeting `src` models; env reads `DATABASE_URL` from environment / `.env` (never commit `.env`; use `.env.example`).
2. Implement models matching [wines_schema.md](../contracts/wines_schema.md):
   - `categories`, `regions`, `sweetness_levels`
   - `wines` with FKs, `dishes` as PostgreSQL `ARRAY(Text)`, `embedding` as `pgvector.Vector(N)`
3. **N:** probe `bin/dinov2_wine_final.onnx` output dim once; put `embedding_dim` in config YAML (e.g. extend `config/compute_cropper.yaml` or new `config/database.yaml`). Do not hardcode magic numbers in call sites.
4. Migration: `CREATE EXTENSION IF NOT EXISTS vector`; create tables; **seed** `sweetness_levels` with: `сухое`, `полусухое`, `полусладкое`, `сладкое`, `брют`, `экстра брют`.
5. Ensure Compose DB is up: `docker compose up -d`; copy `.env.example` → `.env` locally if missing (host URL); `uv run alembic upgrade head`.
6. **Docs (required):** update [`manuals/architecture.md`](../../manuals/architecture.md) — DB components (lookups, wines, pgvector, static images path). Update [`manuals/configuration_guide.md`](../../manuals/configuration_guide.md) — `DATABASE_URL`, embedding_dim, compose. Touch [`manuals/quickstart.md`](../../manuals/quickstart.md) — `docker compose up -d` + alembic. Sync [`manuals/index.md`](../../manuals/index.md) status if stubs become filled. Update [`bin/README.md`](../../bin/README.md) — DINO file already present (`dinov2_wine_final.onnx`).

## Out of scope

- Repository CRUD (1.1), prepare CSV / bulk import (1.2), HTTP search API, YOLO changes.

## Acceptance

- [ ] `alembic upgrade head` succeeds against Compose Postgres
- [ ] Tables `categories`, `regions`, `sweetness_levels`, `wines` exist; sweetness seeded (6 rows)
- [ ] `embedding` column type `vector(N)` with configured N
- [ ] Manuals architecture / configuration_guide / quickstart updated for DB
- [ ] Lint gate: `uv run ruff check src/` (and mypy/bandit per project habit when touching `src/`)

## Handoff

Append to `agent_docs/progress/stage_1.md` (create if needed): `READY_FOR_TEST` only if tester has schema smoke; otherwise `SCHEMA_READY` and proceed to coder_1_1. Tell @Tester nothing mandatory until 1.1 unless you want a migration smoke.
