# Test report — Stage 1.2 Catalog load

**Date:** 2026-09-24  
**Instructions:** `agent_docs/instructions/tester_1_2_catalog_load.md`  
**Contracts:** `catalog_prepare.md`, `wines_schema.md`  
**Verdict:** **PASS**

Full catalog re-import was **not** re-run (parent + Coder handoff already loaded 1950 rows).

## Counts

| Artifact / metric | Expected | Actual |
|-------------------|----------|--------|
| `wines_ready.csv` rows | ~1932 | **1932** |
| `wines_additional.csv` rows | ~15 | **18** |
| `wines_rejected.csv` rows | — | **153** |
| rejected empty `reason` | 0 | **0** |
| Enrich cols on all three (`public_rating`, `serving_temperature`, `alcohol_pct`, `dishes`) | present | **yes** |
| DB `wines` | ready+additional = 1950 | **1950** |
| `embedding IS NULL` | 0 | **0** |
| `image_url` null/empty | 0 | **0** |
| `sweetness_levels` | ≥6 canonical | **6** (`брют`, `полусладкое`, `полусухое`, `сладкое`, `сухое`, `экстра брют`) |
| `static/wines/*.webp` | 1950 | **1950** |

Spot-check: ready slug `fanagoriya-100-ottenkov-krasnogo-kaberne-kaberne-sovinon-krasnoe-suhoe-135` → `static/wines/{slug}.webp` exists (702934 bytes).

## Commands

| Command | Exit code | Result |
|---------|-----------|--------|
| `docker compose ps` | 0 | `db` Up (healthy), port 5432 |
| `uv run alembic current` | 0 | `0001_initial_schema (head)` |
| CSV/SQL probe (Python DictReader + SQLAlchemy) | 0 | counts as above |
| `uv run pytest tests/ -v -k "catalog_load or import"` | 0 | **7 passed**, 6 deselected |

## Cases vs `tester_1_2_catalog_load.md`

| Check | Test-ID / method | Result |
|-------|------------------|--------|
| ready CSV + enrich | 1.2-01 `test_ready_csv_count_and_enrich` | PASS |
| additional CSV + enrich | 1.2-02 `test_additional_csv_count_and_enrich` | PASS |
| rejected + `reason` | 1.2-03 `test_rejected_csv_has_reason` | PASS |
| tables / sweetness / wines / nulls | 1.2-04 `test_lookup_tables_and_wine_counts` | PASS |
| static spot-check | 1.2-05 `test_ready_static_file_spot_check` | PASS |
| `get_by_slug` ready + additional | 1.2-06 `test_get_by_slug_ready_and_additional` | PASS |
| `search_by_embedding` smoke (encode static → top 5) | 1.2-07 `test_search_by_embedding_smoke_imported_image` | PASS |

## Artifacts

- Tests: `tests/test_catalog_load.py` (markers `catalog_load`, `import_check`; registered in `tests/conftest.py`)
- No full re-import; no `src/` changes

## Defects

None.

## Next

Stage 1.2 catalog load verified → stage sign-off / proceed to Stage 2 (eval API) per plan. Out of scope here: owner_eval accuracy, importing `wines_rejected`.
