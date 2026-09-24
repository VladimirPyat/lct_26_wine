# Progress — Stage 1

## 2026-09-24 — Planner

- STATUS: INSTRUCTIONS_READY
- Phase A approved: schema (+ sweetness_levels), prepare ready/additional/rejected, CRUD/vector/filters, hard delete
- Contracts: `wines_schema.md`, `wines_repository.md`, `catalog_prepare.md`; retrieval + infra drafts updated
- Instructions:
  - `coder_1_0_schema.md` → `coder_1_1_crud.md` → `coder_1_2_catalog_load.md`
  - `tester_1_1_crud.md` → `tester_1_2_catalog_load.md`
- paths-access: `static/wines/`, `data/owner_database/`, `data/site_database/`, `scripts/catalog_prepare/`
- Next: @Coder starts `coder_1_0_schema.md`

## 2026-09-24 — Coder (1.0 schema)

- STATUS: SCHEMA_READY
- Done: Alembic + SQLAlchemy models (`categories`, `regions`, `sweetness_levels`, `wines`); `vector(768)`; sweetness seed (6); `config/database.yaml` (`embedding_dim` probed from `bin/dinov2_wine_final.onnx` `pooler_output`); `docker compose` + `alembic upgrade head` OK
- Docs: `manuals/architecture.md`, `configuration_guide.md`, `quickstart.md`, `index.md`; `bin/README.md`; `.gitignore` `/db/` so `src/db/` is tracked
- Lint: `ruff check src/` pass; `bandit -r src/ -ll` pass; `mypy -p db` pass (full `mypy src/` still needs `ml` stubs/deps — pre-existing)
- Next: @Coder `coder_1_1_crud.md` (parent dispatches). No mandatory @Tester until 1.1.

## 2026-09-24 — Coder (1.1 CRUD / DINO / vector)

- STATUS: READY_FOR_TEST
- Done: `DinoOnnxEncoder` + `encode_image` in `src/core/retrieve/`; `WineRepository` (CRUD, slug/upsert, `get_many_by_ids`, `search_by_embedding` cosine→score, `search_filters`); `src/db/session.py`; `src/db/test_support.py` (insert helper + unit vectors + sample image path); `RankedHit` in `core/contracts` (`image_path` ← `wines.image_url`); `config/database.yaml` `dino` preprocess (224 / ImageNet / L2); docs architecture + configuration_guide + index
- Smoke: encode `data/owner_database/images/massandra-rozovoe-suhoe.webp` → len=768, L2≈1.0
- Lint: `ruff check src/` pass; `bandit -r src/ -ll` pass; `mypy -p db` / retrieve blocked by numpy stubs vs `tool.mypy.python_version=3.11` on Py3.12 (env; not Stage 1.1 logic)
- Next: @Tester `tester_1_1_crud.md` (parent dispatches). Do not start coder_1_2 yet.

## 2026-09-24 — Tester (1.1 CRUD / vector)

- STATUS: TEST_PASS
- Commands: `uv run pytest tests/test_wine_repository.py -v` → exit 0 (6 passed, 1.53s); `uv run ruff check src/ tests/` → exit 0
- Report: `agent_docs/reports/test_stage_1_1_crud.md`
- Cases covered: create/get, update modified_at, hard delete, get_many_by_ids, search_by_embedding (DINO), search_filters
- Next: @Coder `coder_1_2_catalog_load.md`

## 2026-09-24 — Coder (1.2 catalog prepare + import)

- STATUS: READY_FOR_TEST (catalog load)
- Prepare: `scripts/catalog_prepare/` — ready=1932, additional=18, rejected=153 (enrich cols; `reason` on rejected); `wines_problem_images.csv` copy; `audit_image_sizes.py` + `image_size_audit.csv`; MIN_SIDE=200; SSOT under `data/` untouched
- Import: `scripts/catalog_import.py` / `src/db/import_catalog.py` — seen=1950 upserted=1950 skipped=0; DB wines=1950, embedding_null=0, image_url empty=0; `static/wines/*.webp`=1950; FastAPI mount `/static/wines`
- Deps: Pillow in extra `ml` (`uv add --optional ml pillow`)
- Docs: quickstart / configuration_guide / architecture / index (+ README layout paths)
- Lint: `uv run ruff check src/ scripts/` exit 0; `uv run bandit -r src/ -ll` exit 0
- Next: @Tester `tester_1_2_catalog_load.md` (parent dispatches). Do not re-run full import unless Tester finds gaps.

## 2026-09-24 — Tester (1.2 catalog load)

- STATUS: TEST_PASS
- Report: `agent_docs/reports/test_stage_1_2_catalog_load.md`
- Counts: ready=1932, additional=18, rejected=153 (reason filled); DB wines=1950; emb_null=0; image_url empty=0; sweetness=6; static webp=1950
- Commands: `docker compose ps` exit 0 (healthy); `uv run alembic current` exit 0 (`0001_initial_schema`); `uv run pytest tests/ -v -k "catalog_load or import"` exit 0 (7 passed)
- Tests: `tests/test_catalog_load.py` (1.2-01…1.2-07); no full re-import
- Next: stage sign-off / Stage 2 per plan
