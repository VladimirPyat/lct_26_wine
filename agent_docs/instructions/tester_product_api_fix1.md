# @Tester — PROD-API fix1: analogs by grape + OCR fallback chain

**After:** `READY_FOR_TEST (PROD-API-FIX1)` in `agent_docs/progress/stage_3.md` · **Branch:** `feat/product-api` · **Worktree:** `/work/lct_vine_final/.worktrees/api`  
**Contracts:** [`../contracts/product_api.md`](../contracts/product_api.md) §4.2 · [`../contracts/ocr_engine.md`](../contracts/ocr_engine.md) «Engine selection» · **Coder spec:** [`coder_product_api_fix1.md`](coder_product_api_fix1.md)  
**Scope:** `tests/` only (not `tests/web/`). Never edit `src/` / `config/`; defects → report for @Coder.

## Environment

```bash
cd /work/lct_vine_final/.worktrees/api
export UV_PROJECT_ENVIRONMENT=/work/lct_vine_final/.venv UV_NO_SYNC=1   # never uv sync
```

Shared Postgres read-only (`@pytest.mark.db`; report env-skips honestly). No real GPU / LLM / network in unit tests — use monkeypatch / fakes. Live server (optional, §D): background `nohup`, bounded readiness loop, `curl --max-time`, `timeout`; port 8081 only; stop it afterwards.

## A. Replace tests that encode the old chain (owner decisions 2026-09-28)

Update expectations, keep `[TEST-ID]`s (suffix `-fix1`); do not delete coverage silently — each removed assertion must be replaced by the new rule:

| Test | Old expectation | New expectation |
|---|---|---|
| `test_product_service_db.py::test_analogs_for_found_winner_filters` (PA-B3) | `filters.color == winner.color` | `filters.color is None`; `filters.grape` = winner's first grape (dictionary-canonical); every result wine has that grape as a whole `grape_variety` element; manufacturer ≠ winner's; winner excluded; `hints.color == winner.color`, `hints.ocr_ran is False` |
| `…::test_analogs_ocr_filters_color_and_grape` (PA-B4) | `filters.color == "Белое"` | `filters.color is None`, `filters.grape == "Шардоне"`; wines all contain the grape; colors not constrained; `hints` preserved |
| `…::test_analogs_fallback_impossible_grape_to_color` (PA-B5) | retry color-only | impossible grape → `source == "ocr_filters"`, `wines == []`, `total == 0`, `filters.grape` = the impossible grape |
| `…::test_analogs_fallback_impossible_color_to_vector` (PA-B5b) | `vector` rank 2..K | color hint + no grape → `ocr_filters`, empty, `total == 0` (color is never a filter) |
| `…::test_analogs_no_hints_vector` (PA-B5c) | `vector` | `ocr_filters`, empty, `total == 0`, `filters.grape is None` |
| `…::test_analogs_winner_fallback_chain` (PA-B5d) | `vector` | winner with non-matching grape → `winner_filters`, empty, `total == 0`; winner without grape (`grape_variety=""`) → empty, and **no DB query** (spy on `WineRepository.count_filters` / `search_filters` → not called) |
| `test_product_api.py::test_search_low_uses_ocr_hint_analogs` (PA-C1b) | OCR «КРАСНОЕ СУХОЕ» → color filter | same lines → `hints.color == "Красное"` but `wines == []`, `total == 0`; add a sibling case with lines containing a grape (e.g. «КАБЕРНЕ СОВИНЬОН») → `ocr_filters`, non-empty, winner excluded |
| `test_product_api.py::test_search_low_rerank_switch_vector_excludes_winner` (PA-C1d, DEF-1) | `vector` without winner | rename → `…_rerank_switch_no_grape_empty`: rerank switched to rank 2, OCR «2019» → `source == "ocr_filters"`, `wines == []`; and with a grape line → `exclude_slugs == [winner.slug]` where winner = rank-2 slug, winner not in wines. DEF-1 closed as obsolete |
| `test_product_api.py::test_found_analogs_endpoint` (PA-C2c) | `source in {winner_filters, vector}` | `source == "winner_filters"` only; `filters.color is None` |

Global: `grep -rn '"vector"' tests/test_product_*.py` — only allowed in stub-backed tests (`StubProductService` may still emit it).

## B. New tests — analogs

`tests/test_product_service_db.py` (`@pytest.mark.db`):
- [ ] **found, no OCR**: monkeypatch `service._runtime.get_ocr` (and `api.eval_pipeline.recognize_crop` as used by the service) to raise / count calls → `analogs_for(found)` makes **zero** OCR calls; result per A row PA-B3.
- [ ] **found, blend winner** (`grape_variety` with `,` / `/`): filter uses the first element after split + canonicalization.
- [ ] `limit` / `total`: `total == find_wines(filters, limit=ALL)[1]`, first `limit` equal to `find_wines` order (rating DESC NULLS LAST, id).
- [ ] **unknown with Latin grape** via `search` flow (reuse the `flow` fixture in `test_product_api.py`): `pipeline.ocr_lines = ["CABERNET SAUVIGNON", "RED DRY WINE"]`, `score_1` in `low` range → `ocr_filters`, `filters.grape == "Каберне Совиньон"`, `filters.color is None`, `hints.color == "Красное"`, winner excluded, all wines contain the grape.
- [ ] **unknown without grape**: `not_found` + lines «ROSSO 2019» → empty, `total == 0`, `exclude_slugs == []`.
- [ ] **OCR unavailable in search**: runtime OCR `None` (or raising `OCRUnavailableError`) on a `low` search → 200, `analogs.hints.ocr_ran is False`, empty analogs.

`tests/test_product_hints.py` (pure, no DB):
- [ ] `grape_aliases={"Санджовезе": ["sangiovese"], "Пино Нуар": ["pinot noir", "pinot nero"]}`, dictionary containing «Санджовезе», «Пино Нуар», «Пино Гри»: «SANGIOVESE» → `["Санджовезе"]`; «PINOT NOIR» / «Pinot Nero» → «Пино Нуар»; «PINOT» alone → `[]`; «ПИНО» alone → `[]`; «PINOT GRIS» → «Пино Гри» (via `_TOKEN_ALIASES`) and not «Пино Нуар»; «CABERNET SAUVIGNON» still → «Каберне Совиньон»; diacritics («GEWÜRZTRAMINER» with alias `gewurztraminer`) match.
- [ ] Default `grape_aliases` absent → identical results to the old tests (backward compatible).
- [ ] Config: `load_product_settings()` on the repo `product.yaml` loads; every `grape_aliases` key exists in the DB grape dictionary (`@pytest.mark.db`) — or the service logs a warning and ignores unknown keys (assert the log via `caplog`).

## C. New tests — OCR fallback chain (no GPU / LLM needed)

New `tests/test_ocr_selection.py` against the pure selection function + runtime wiring (monkeypatch):
- [ ] `phocr` + `cuda_available=True` → effective `phocr`, reason `cuda_available`, LLM probe **not** called.
- [ ] `phocr` + `cuda_available=False` + probe returns a fake engine → effective `llm`, reason `no_cuda`.
- [ ] `phocr` + no CUDA + probe raises `ValueError("Environment variable 'QWEN_API_KEY' is missing…")` → effective `none`, reason starts with `llm_unavailable`, `engine is None`; reason contains no key value (set a fake env value in another test and assert it never appears in reason / `caplog`).
- [ ] `llm` configured → probe called regardless of CUDA; failure → `none`.
- [ ] `mock` → `mock`, probe not called.
- [ ] CUDA detection helper: `compute.device="cpu"` → False; `"cuda"` + fake encoder session `get_providers()==["CPUExecutionProvider"]` → False; with `CUDAExecutionProvider` → True (monkeypatch `ort.get_available_providers` to include CUDA in the False case to prove it is not the only signal).
- [ ] GPU path arguments: with effective `phocr`, `get_ocr()` calls `create_ocr_engine("phocr", use_cuda=True, lang=…, limit_side_len=…, ort_threads=…)` exactly once (monkeypatched factory; lazy — not called before first `get_ocr()`).
- [ ] Startup log: one INFO record `OCR engine: configured=… effective=… reason=…` (`caplog`).

`tests/test_policy_decision.py` (extend):
- [ ] `ocr_factory=lambda: None` on a near-tie → `slug == hits[0]["slug"]`, `rerank_triggered is False`, `rerank_reason == "ocr_unavailable"`.
- [ ] fake engine raising `OCRUnavailableError` → same, `rerank_reason == "ocr_failed"`.
- [ ] fake engine raising `RuntimeError` (PHOCR-like) → propagates (not swallowed).
- [ ] existing decide tests unchanged and green (GPU semantics).

`tests/test_ocr_adapter.py` (extend): LLM engine whose `complete` raises (openai-like error / `RuntimeError`) → `LLMOCREngine`/wrapper raises `OCRUnavailableError` with `__cause__` set; missing image still `FileNotFoundError`.

Eval endpoint with effective `none` (TestClient + fake runtime or monkeypatched `get_ocr → None`): `/v1/eval/predict` near-tie → 200 `{"slug": top-1}`.

## D. Regression

- [ ] `uv run python scripts/eval_ocr_gate.py --margins 0.08` → exit 0, JSON identical to the pre-fix1 run (it passes its own `ocr_factory`).
- [ ] Decision log: eval lines still contain `score_1`, `score_2`, `rerank_reason`; product lines `search_id`, `status`.
- [ ] owner_eval sets 1/2 via `:8081/v1/eval/predict` vs `data/tmp/baseline_master_set{1,2}.jsonl` — **only if the GPU is free** (startup log `effective=phocr`): 52/52 identical. On a CPU-only server the chain selects LLM/none → record results as informational (OCR-tie queries `q-000004`, `q-000020` may differ), not as a regression verdict. Owner does not require live GPU re-verification now (decision E).

## Commands

```bash
uv run ruff check src/ tests/
timeout 1200 uv run pytest tests/ -v -rs
uv run pytest tests/test_product_service_db.py tests/test_product_api.py tests/test_product_hints.py \
  tests/test_ocr_selection.py tests/test_policy_decision.py tests/test_ocr_adapter.py -v -rs
```

## Report + commit

- Report `agent_docs/reports/test_product_api_fix1.md` (A/B/C/D counts, env-skips, defects with repro); append `TEST_PASS` / `TEST_FAIL (PROD-API-FIX1)` to `agent_docs/progress/stage_3.md` (append-only).
- Commits only `test(product-api): …`, only your files: `git commit -m "test(product-api): …" -- <paths>`. No push / merge.
