# Test report — Stage 1.1 CRUD / vector

**Date:** 2026-09-24  
**Instructions:** `agent_docs/instructions/tester_1_1_crud.md`  
**Verdict:** **PASS**

## Commands

| Command | Exit code | Result |
|---------|-----------|--------|
| `uv run pytest tests/test_wine_repository.py -v` | 0 | 6 passed in 1.53s |
| `uv run ruff check src/ tests/` | 0 | All checks passed |

DB: Compose Postgres already up (no `docker compose` / alembic re-run this pass). Alembic head assumed `0001_initial_schema` per parent.

## Cases vs `tester_1_1_crud.md`

| # | Case | Test | Result |
|---|------|------|--------|
| 1 | create + get_by_id + get_by_slug | `test_create_get_by_id_and_slug` | PASS |
| 2 | update / `modified_at` | `test_update_moves_modified_at` | PASS |
| 3 | hard delete | `test_hard_delete` | PASS |
| 4 | get_many_by_ids | `test_get_many_by_ids` | PASS |
| 5 | search_by_embedding (real DINO) | `test_search_by_embedding_rank1` | PASS |
| 6 | search_filters | `test_search_filters` | PASS |

## Notes

- First sandbox run failed with `Connection refused` to `127.0.0.1:5432` (sandbox network); re-run outside sandbox → green.
- No product defects. Out of scope: catalog load counts, Hit@1 / owner_eval, HITL.

## Next

@Coder `coder_1_2_catalog_load.md`.
