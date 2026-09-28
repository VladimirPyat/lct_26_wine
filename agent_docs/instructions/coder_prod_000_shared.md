# @Coder — PROD-000: shared product contract code (run on `master` before branching)

**Branch:** `master` (after `feat/siglip-prod` is merged). Small, self-contained; both parallel branches start from this commit.  
**Plan:** [`../plans/web_product.md`](../plans/web_product.md) · **Contract:** [`../contracts/product_api.md`](../contracts/product_api.md) §1–3, §6

## Steps

1. `src/core/product/schemas.py` — DTOs exactly as contract §2 (Pydantic v2; `model_config = ConfigDict(frozen=True)` where practical). No extra fields.
2. `src/core/product/service.py` — `ProductService` Protocol (§3), `SearchNotFoundError(LookupError)`, `UploadRejectedError(ValueError)`. Docstrings in Russian.
3. `src/core/product/stub.py` — `StubProductService` per §3 «Stub behaviour»:
   - 5 fixture wines; `image_url` points to existing files `/static/wines/{slug}.webp` of 5 real catalog slugs if present, otherwise any string (UI must handle broken images);
   - `search` copies the file to a `tempfile.mkdtemp()` dir, status by `original_name` keyword (`notfound` / `low` / default found+high), analogs filled for low/not_found (`source="ocr_filters"` with a fake hint), `candidates` = 5 fixtures with descending scores;
   - thread-safe in-memory dicts (`threading.Lock`).
4. `src/core/product/__init__.py` — re-export public names.
5. `config/product.yaml` — contract §6 verbatim (placeholders). `src/core/config.py`: `ProductSettings` (nested models: `ConfidenceSettings` with `not_found_min ≤ medium_min ≤ high_min` validator, `AnalogSettings`, `StorageSettings`, `UploadSettings`) + `load_product_settings(path=None)` following existing loader style.
6. `src/api/main.py` lifespan: `app.state.product_settings = load_product_settings()`; `app.state.product_service = StubProductService()` — keep it one clearly marked line (backend branch replaces it). No routes yet.
7. `.gitignore`: `data/tmp/search_queries/`, `data/tmp/search_feedback.jsonl` (if `data/tmp/` is not already ignored).

## Verification

```bash
uv run ruff check src/
uv run mypy src/core/product/ --ignore-missing-imports
uv run pytest tests/ -v -k "not owner_eval"
```

Smoke (no DB): `python -c` — create stub, `search()` on a temp jpg named `x_notfound.jpg` → `status == "not_found"`, `winner is None`, `analogs.wines` non-empty; round-trip `SearchResult.model_validate_json(r.model_dump_json())`.

## Acceptance

- [ ] Types match contract §2–3 exactly
- [ ] Stub covers found / low / not_found, feedback, filters, dictionaries
- [ ] `product.yaml` + loader + validator
- [ ] App starts (`uvicorn`) with stub on `app.state`; `/v1/eval/predict` unaffected
- [ ] Commit on `master`: `feat(product): shared DTOs, ProductService protocol, stub, product.yaml`

Handoff: append `READY (PROD-000)` to `agent_docs/progress/stage_3.md` (create with header if missing). Then human creates worktrees (plan §Worktrees).
