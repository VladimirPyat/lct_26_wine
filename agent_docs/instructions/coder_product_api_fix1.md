# @Coder — PROD-API fix1: owner decisions on analogs + OCR fallback chain (2026-09-28)

**Branch:** `feat/product-api` · **Worktree:** `/work/lct_vine_final/.worktrees/api` (all edits + commits here) · **API port:** 8081  
**Contracts:** [`../contracts/product_api.md`](../contracts/product_api.md) §4.1 step 5, §4.2, §6 · [`../contracts/ocr_engine.md`](../contracts/ocr_engine.md) «Engine selection»  
**Context:** [`../reports/test_product_api.md`](../reports/test_product_api.md) (DEF-1 — now obsolete), [`../reports/BLOCKED.md`](../reports/BLOCKED.md) (PROD-API question — resolved)  
**Do not touch:** `src/web/`, `tests/`, `tests/web/`, DTO / Protocol shapes in `core/product/schemas.py` / `service.py` (keep `AnalogSource` Literal incl. `"vector"`), `StubProductService`, `config/ocr_rerank.yaml` / `config/compute_cropper.yaml` defaults, `confidence.*` thresholds in `product.yaml`, `core/text/normalize.py::_TOKEN_ALIASES` (eval-sensitive).  
**No** new packages, no `uv sync`, no downloads.

## Environment (mandatory)

```bash
cd /work/lct_vine_final/.worktrees/api
export UV_PROJECT_ENVIRONMENT=/work/lct_vine_final/.venv UV_NO_SYNC=1   # shared venv; NEVER run uv sync
```

- Shared Compose Postgres (started from the main folder) — **read-only** use; no imports / migrations / writes except the app's own `data/tmp/*` files.
- Long-running servers: background with `nohup … > data/tmp/<name>.log 2>&1 &`, record the PID, bounded readiness loop (e.g. ≤ 120 × 1 s `curl --max-time 2 -sf http://127.0.0.1:8081/health` or any cheap route), every `curl` with `--max-time`, wrap long commands in `timeout`. Stop the server (`kill <pid>`) when done; do not touch `:8080`.

## Steps

### FIX1-001 — Analogs rewrite (`src/core/product/catalog_service.py`), contract §4.2

- **A. Known wine** (`analogs_for` with `status == "found"`): no OCR call. `grape = self._grapes.canonical(split_grapes(winner.grape_variety)[0])` (current helper). Filters: `CatalogFilters(grape=grape, exclude_manufacturer=winner.manufacturer, exclude_slugs=[winner.slug])` — **no `color`**. Hints: `OcrHints(color=winner.color, grapes=[grape] if grape else [], ocr_ran=False)`. Source `winner_filters`.
- **B. Unknown wine** (`low` / `not_found`, in `search` and in `analogs_for` from stored `analogs.hints`): `CatalogFilters(grape=hints.grapes[0] if hints.grapes else None, exclude_slugs=[winner.slug] if winner else [])` — **no `color`**. Hints unchanged (full OCR hints). Source `ocr_filters`.
- Common: `grape is None` → return `AnalogsResult(source, filters, hints, wines=[], total=0)` **without a DB query**. Else one `_find(repo, filters, limit, 0)`; `total == 0` → empty result, same source. No retry.
- Delete `_vector_analogs` and the color-only retry in `_filtered_analogs` (collapse into one helper). `candidates` is no longer needed by analog helpers — drop the parameter. `grep -n '"vector"' src/core/product/catalog_service.py` must be empty.
- `_hints`: OCR unavailable (`runtime.get_ocr()` is `None`, see FIX1-003) or OCR raises → `OcrHints(ocr_ran=False)` (log at WARNING once per request, no stack trace spam for `OCRUnavailableError`). When rerank ran but the policy reports `rerank_reason in {"ocr_unavailable", "ocr_failed"}`, treat as no OCR (do not call OCR again).
- Docstrings (Russian) updated; no «vector» wording left in the real service.

### FIX1-002 — Grape hints across scripts (`src/core/product/hints.py`, `config/product.yaml`, `src/core/config.py`)

- Keep the existing whole-name path (`reranker.label_evidence` over dictionary grapes) — it already handles Cyrillic, transliteration and `_TOKEN_ALIASES` (cabernet, sauvignon, merlot, chardonnay, riesling, saperavi, pinot, noir, blanc, gris, syrah, shiraz, muscat, tempranillo).
- Add product-only Latin aliases: `analogs.grape_aliases: dict[str, list[str]]` in `ProductSettings.analogs` (default `{}` so the web branch's `product.yaml` keeps loading; validator: keys non-empty, values non-empty strings). Fill `config/product.yaml` for **dictionary grapes** (take the real list from `service.dictionaries().grapes` / the DB — read-only) that have international names, e.g. Санджовезе → sangiovese; Пино Нуар → pinot noir, pinot nero; Пино Гри / Пино Гриджо (whichever is in the dictionary) → pinot gris, pinot grigio; Неббиоло → nebbiolo; Мальбек → malbec; Гренаш → grenache, garnacha; Примитиво → primitivo, zinfandel; Совиньон Блан → sauvignon blanc; Шенен Блан → chenin blanc; Гевюрцтраминер → gewurztraminer; Вионье → viognier; Монтепульчано → montepulciano; Неро д'Авола → nero d'avola; Карменер → carmenere; Пти Вердо → petit verdot; Алиготе → aligote; Ркацители → rkatsiteli; Каберне Фран → cabernet franc; etc. **Only keys that exist in the dictionary** (log a WARNING at startup for unknown keys and ignore them). Adding keys to `product.yaml` is allowed; thresholds stay untouched.
- Matching of an alias phrase: fold (lowercase, ё→е, strip diacritics — reuse `_fold`), all alias tokens must be present among OCR words (whole phrase, token order free); a one-token alias must not match a grape whose canonical name has more tokens unless that grape is the alias key (e.g. alias `pinot` does not exist; «PINOT» alone → no «Пино Нуар»). Union with the `label_evidence` matches, then the existing ordering (more tokens first, then dictionary order).
- `extract_hints` / `extract_grapes` get an optional `grape_aliases` argument (default empty → current behaviour; existing unit tests stay valid).
- Must hold: «CABERNET SAUVIGNON» → «Каберне Совиньон»; «SANGIOVESE» → «Санджовезе» (if in dictionary); «PINOT NOIR» → «Пино Нуар»; «ПИНО» alone → no «Пино Гри» / «Пино Нуар».

### FIX1-003 — OCR engine fallback chain (`src/api/runtime.py`, `src/core/ocr/`, `src/core/policy/decision.py`, `src/llm/adapters/ocr.py`)

Per `ocr_engine.md` «Engine selection»:
- `core/ocr/base.py`: add `class OCRUnavailableError(RuntimeError)`.
- Pure selection function (e.g. `core/ocr/selection.py::select_ocr_engine(configured: str, *, cuda_available: bool, llm_probe: Callable[[], IOCREngine]) -> OcrSelection(effective: Literal["phocr","llm","mock","none"], reason: str, engine: IOCREngine | None)`): `phocr`+CUDA → `phocr` (engine built lazily later, `engine=None` here is fine); `phocr` without CUDA → try `llm_probe()`; `llm` → try `llm_probe()`; probe raises (`ValueError` missing key, `FileNotFoundError`, `TypeError`, any init error) → `none` with a reason that contains the exception class + message **without** secret values (the factory message names only the env var — OK); `mock` → `mock`.
- CUDA available: `compute.device == "cuda"` **and** the built image encoder's ORT session reports `CUDAExecutionProvider` among its active providers (`session.get_providers()`); if the encoder does not expose the session, add a small accessor — do not create new sessions / models. `ort.get_available_providers()` alone is **not** sufficient (lists CUDA with `CUDA_VISIBLE_DEVICES=""`).
- `build_eval_runtime`: run selection once, store on `EvalRuntime` (e.g. `ocr_effective`, `ocr_reason`), log one INFO line `OCR engine: configured=%s effective=%s reason=%s`. LLM probe at startup = `create_llm_engine(ocr.llm_task)` (no network call).
- `EvalRuntime.get_ocr() -> IOCREngine | None`: `phocr` → build lazily exactly as today (`create_ocr_engine("phocr", use_cuda=True, lang, limit_side_len, ort_threads)`; same arguments as the current GPU path); `llm` → the probed engine wrapped fail-soft; `mock` → `MockOCREngine`; `none` → `None`.
- LLM fail-soft: `LLMOCREngine.recognize` (or a thin wrapper in runtime) converts LLM call errors (openai errors, `RuntimeError` empty content) into `OCRUnavailableError` (chain the cause; log task name only). `FileNotFoundError` for a missing crop stays as is.
- `decide(...)`: `ocr_factory: Callable[[], IOCREngine | None]`. Factory returns `None` → return the skip-rerank decision (`rerank_triggered=False`, `rerank_reason="ocr_unavailable"`). `recognize` raises `OCRUnavailableError` → same skip decision with `rerank_reason="ocr_failed"`. Catch **only** `OCRUnavailableError` (PHOCR errors propagate as today). Existing callers passing a non-None factory (`scripts/eval_ocr_gate.py`, `scripts/simulate_ocr_rerank.py`) must keep working unchanged.
- `api/eval_pipeline.recognize_crop` → `list[str] | None` (`None` when no engine).
- `scripts/calibrate_confidence.py --ocr-device cpu`: now yields LLM / none per chain — update its help text / docstring only.
- Decision log: no new mandatory fields; `rerank_reason` already logged. (Optional: add `ocr_engine_effective` to the log record only if `tests/test_product_decision_log.py` expectations still hold — otherwise skip.)
- `ocr.engine: mock` / explicit `llm` keep their meaning (no CUDA check); explicit `llm` without key → effective `none` (chain step «LLM unavailable»), not a crash.

### FIX1-004 — Manuals (Russian)

- `manuals/architecture.md`: «Аналоги» section rewritten per §4.2 (известное вино — сорт победителя из БД без OCR, исключая производителя; неизвестное — только сорт из OCR; нет сорта / 0 совпадений → пусто; `vector` не выдаётся); OCR paragraph → цепочка выбора движка (CUDA → PHOCR, нет CUDA → LLM, нет LLM → без OCR, rerank пропускается); `api.runtime` row.
- `manuals/configuration_guide.md`: `analogs.grape_aliases`; section «OCR backend» — цепочка, строка лога при старте, что `ocr.engine`/`compute.device` дефолты не менялись, профили GPU/CPU — `CFG-DEVICE-001`.
- `manuals/quickstart.md`: `/analogs` sources line (`winner_filters` / `ocr_filters`; пустой список = «аналог подобрать не удалось»); CPU запуск без ключа LLM → OCR отключён.
- `manuals/manual_testing.md` §5: add a check «`compute.device: cpu` + ключ LLM → в логе старта `effective=llm`; без ключа → `effective=none`, slug всё равно возвращается».

## Verification

```bash
cd /work/lct_vine_final/.worktrees/api
export UV_PROJECT_ENVIRONMENT=/work/lct_vine_final/.venv UV_NO_SYNC=1
uv run ruff check src/ scripts/
uv run mypy src/core/product/ src/core/ocr/ src/api/ --ignore-missing-imports --python-version 3.12   # 0 new errors in touched modules
uv run bandit -r src/ -ll
timeout 1200 uv run pytest tests/ -v -rs     # old analog tests (vector / color-only / DEF-1) are expected to fail until @Tester fix1 — list them in progress, do not edit tests/
```

Server + eval regression (GPU; the GPU path must stay byte-identical):

```bash
nohup uv run uvicorn api.main:app --app-dir src --host 127.0.0.1 --port 8081 > data/tmp/fix1_8081.log 2>&1 &
echo $! > data/tmp/fix1_8081.pid
for i in $(seq 1 120); do curl --max-time 2 -sf -o /dev/null http://127.0.0.1:8081/api/v1/dictionaries && break; sleep 1; done
grep -m1 "OCR engine:" data/tmp/fix1_8081.log     # expect effective=phocr reason=cuda_available on GPU
timeout 1800 ./data/owner_eval/1/participant_test.sh --images-dir ./data/owner_eval/1/queries --manifest ./data/owner_eval/1/queries.tsv \
  --endpoint 'http://127.0.0.1:8081/v1/eval/predict' --output ./data/tmp/fix1_set1.jsonl
timeout 1800 ./data/owner_eval/2/participant_test.sh --images-dir ./data/owner_eval/2/queries --manifest ./data/owner_eval/2/queries.tsv \
  --endpoint 'http://127.0.0.1:8081/v1/eval/predict' --output ./data/tmp/fix1_set2.jsonl
# compare slugs per query id with data/tmp/baseline_master_set1.jsonl / baseline_master_set2.jsonl → must be identical (52/52)
curl --max-time 60 -sf -F image=@data/owner_eval/1/queries/<file> http://127.0.0.1:8081/api/v1/search    # found → analogs null
curl --max-time 30 -sf "http://127.0.0.1:8081/api/v1/search/<id>/analogs?limit=5"                     # winner_filters, grape set, color null
kill "$(cat data/tmp/fix1_8081.pid)"
```

- If the GPU is busy (`:8080` holds VRAM) and the set cannot run on GPU: report it in progress as env-limited; do **not** claim byte-identity from a CPU run (on CPU the chain now selects LLM/none — slugs may legitimately differ on OCR-tie queries `q-000004`, `q-000020`). Live GPU re-verification is not required by the owner at this step (decision E), but run it if the GPU is free.
- In-process checks (no models): low + OCR lines «SANGIOVESE / ROSSO» → `ocr_filters`, `grape=Санджовезе`, `color=None`; low + «2019» → empty, `total=0`; runtime selection with `compute.device=cpu` and no LLM key → `effective=none`, `/v1/eval/predict` still returns a slug.

## Acceptance

- [ ] Real service never returns `source="vector"`; no color-only retry; no DB query when `grape is None`
- [ ] Found analogs: no OCR call, filter = winner grape + `exclude_manufacturer` + `exclude_slugs=[winner]`, `color=None`; hints carry winner color
- [ ] Unknown analogs: only OCR grape; Latin / transliterated grape names map to dictionary grapes; «ПИНО» ≠ «Пино Гри»
- [ ] OCR chain per `ocr_engine.md`; one startup log line; `none` / per-request LLM failure → rerank skipped, no 500
- [ ] GPU eval regression 52/52 identical to `data/tmp/baseline_master_set{1,2}.jsonl` (or documented env limitation)
- [ ] DTO / Protocol / stub unchanged; `ocr_rerank.yaml`, `compute_cropper.yaml`, `product.yaml` thresholds unchanged
- [ ] ruff / bandit clean; manuals updated (Russian)

## Commit + handoff

- Commits only with prefix `feat(product-api): …`, only your files: `git commit -m "feat(product-api): …" -- <paths>`. No push / merge.
- Append `READY_FOR_TEST (PROD-API-FIX1)` to `agent_docs/progress/stage_3.md` (append-only) with commands + exit codes, list of old tests expected to fail → @Tester [`tester_product_api_fix1.md`](tester_product_api_fix1.md).
