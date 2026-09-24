# @Tester — Stage 1.1 CRUD + vector unit tests

**After:** @Coder finishes [`coder_1_1_crud.md`](coder_1_1_crud.md) (`READY_FOR_TEST` in progress).  
**Contracts:** [`../contracts/wines_repository.md`](../contracts/wines_repository.md)

## Goal

Unit/integration tests against a real Postgres (Compose) with **2–3** wine rows and real (or fixture) embeddings. Prove CRUD, slug, filters, and vector top-K. **Not** search accuracy / owner_eval.

## Setup

```bash
docker compose up -d
# ensure .env present (from .env.example)
uv sync --extra ml --extra db --extra dev
uv run alembic upgrade head
```

Prefer pytest with DB session fixture; isolate test data (unique slug prefix) and hard-delete after, or use a disposable schema if already patterned.

## Cases (minimum)

1. **create + get_by_id + get_by_slug** — required fields + embedding + image_url  
2. **update** — changes field; `modified_at` moves forward  
3. **hard delete** — row gone; get returns None  
4. **get_many_by_ids** — returns requested ids  
5. **search_by_embedding** — insert 2–3 wines with distinct embeddings; query with one wine’s vector → that slug in top_k (ideally rank 1)  
6. **search_filters** — at least: filter by category_name; rating_min; dish overlap if dishes set; sort_by_rating  

Encoding: use project DINO encoder on small real images, or vectors of length N that are orthogonal enough for a smoke ranking — prefer at least one path through real encoder if CI machine has `bin/` weights.

## Commands

```bash
uv run pytest tests/ -v -k "wine or catalog or repository"   # adjust to actual paths
uv run ruff check src/ tests/
```

## Out of scope

- Full catalog row counts (tester_1_2)
- Hit@1 / owner_eval (Stage 2)
- HITL / `manual_testing.md` not required for this slice

## Report

Write `agent_docs/reports/test_stage_1_1_crud.md`: commands, pass/fail, short notes. Append status to `agent_docs/progress/stage_1.md`.
