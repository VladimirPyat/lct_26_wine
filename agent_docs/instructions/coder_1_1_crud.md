# @Coder — Stage 1.1 CRUD, DINO encode, vector search

**Depends on:** [`coder_1_0_schema.md`](coder_1_0_schema.md)  
**Contracts:** [`../contracts/wines_repository.md`](../contracts/wines_repository.md), [`../contracts/retrieval.md`](../contracts/retrieval.md), [`../contracts/wines_schema.md`](../contracts/wines_schema.md)  
**Tester:** [`tester_1_1_crud.md`](tester_1_1_crud.md)

## Goal

Implement wine repository (CRUD, slug, filters, `search_by_embedding`) and a **DINO ONNX encoder** so tests can insert 2–3 real embeddings. YOLO crop is **not** required for these fixtures (encode full bottle images).

## Dependencies (approved)

```bash
uv sync --extra ml --extra db --extra dev
```

Reuse existing YOLO stack only if helpful; do not block on cropper for unit fixtures.

## Steps

1. **DINO encoder** in `src/core/retrieve/` (package was empty):
   - Load `bin/dinov2_wine_final.onnx` (+ `.onnx.data` sidecar as required by ORT)
   - Preprocess consistent with model export (document size/normalize in config)
   - `encode_image(path) -> list[float]` length `embedding_dim`
   - Wire `dino_model_path` + device/threads in config / `AppSettings` (extend existing YAML)

2. **Repository** per [wines_repository.md](../contracts/wines_repository.md):
   - CRUD by id (hard delete), list pagination
   - `get_by_slug`, `upsert_by_slug`
   - `get_many_by_ids`
   - `search_by_embedding(embedding, top_k=5)` → `RankedHit`-compatible results
   - `search_filters(...)` with optional AND filters (category, sweetness, region, manufacturer, grape ILIKE, dish overlap, rating/alcohol min/max, sort by rating)
   - No `title ILIKE`; no vector+filter combo SQL

3. **Test support:** small helper or fixture path to insert wines with required fields + embedding from encoder (or precomputed vector of length N for pure SQL unit tests — prefer at least one test that runs real DINO on a tiny local image under `tests/fixtures/` or a known file under `data/owner_database/images/` if available in env).

4. **Docs (required):** extend [`manuals/architecture.md`](../../manuals/architecture.md) — retrieve/encode → pgvector top-K; repository boundaries. Extend [`manuals/configuration_guide.md`](../../manuals/configuration_guide.md) — DINO path, device, embedding_dim. Update RankedHit/image field naming if `image_url` vs `image_path` diverges — keep contracts and code aligned.

## Out of scope

- Bulk CSV prepare/import (1.2)
- Eval HTTP `/v1/eval/predict` (Stage 2)
- Search accuracy benchmarks

## Acceptance

- [ ] Encoder returns vector of configured dim
- [ ] Repository methods exist and match contract signatures
- [ ] Can insert ≥2 wines with embeddings and run `search_by_embedding` returning ordered hits
- [ ] Hard delete removes row
- [ ] Docs updated
- [ ] `uv run ruff check src/` (+ mypy/bandit as usual)

## Handoff

Append `READY_FOR_TEST` to `agent_docs/progress/stage_1.md` → @Tester runs [`tester_1_1_crud.md`](tester_1_1_crud.md).
