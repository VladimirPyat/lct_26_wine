# @Coder — OPT-001 + OPT-002 (DINO batch encode + YOLO cropper.device)

**Depends on:** Stage 1.2 catalog load, `fix_catalog_yolo_encode` (done)  
**Contract:** [`../contracts/compute_opt.md`](../contracts/compute_opt.md)  
**Plan:** [`../plans/opt_001_002.md`](../plans/opt_001_002.md)  
**Tester:** [`tester_opt_001_002.md`](tester_opt_001_002.md)  
**Deps:** none new — do **not** `uv add` / touch lockfiles.

Implement **section A first**, then **B**, then manuals + lint. One PR / one handoff is OK.

---

## Goal

1. **OPT-001:** Batched DINO `encode_images` + wire catalog import to `dino.encode_batch_size` (default 16; `1` = serial).
2. **OPT-002:** `cropper.device: cpu|cuda|auto` (default **cpu**) drives YOLO ORT providers; online eval stays CPU YOLO unless overridden.
3. Update Russian manuals (remove “YOLO always CPU”).

---

## Files to touch (exact)

| Area | Paths |
|------|--------|
| Config YAML | `config/database.yaml`, `config/compute_cropper.yaml` |
| Settings | `src/core/config.py` (`DinoPreprocessSettings`, `CropperSettings`) |
| DINO | `src/core/retrieve/dino_encoder.py` |
| YOLO | `src/core/cropper/onnx_yolo.py` |
| Import CLI | `src/db/import_catalog.py` (batch encode + optional CLI overrides) |
| Manuals (RU) | `manuals/architecture.md`, `manuals/configuration_guide.md`, `manuals/quickstart.md`; sync `manuals/index.md` if TOC needs it |
| Progress | append `READY_FOR_TEST` to `agent_docs/progress/stage_2.md` (or `opt.md` if you create one — prefer stage_2) |

Do **not** edit `.cursor/`, `docs/`, `tests/` (Tester owns tests), Planner contracts.

---

## A. OPT-001 — Batched DINO encode

### A1. Config + settings

1. In `config/database.yaml` under `dino:`, add:

   ```yaml
   encode_batch_size: 16   # 1 = serial; catalog import / re-encode ORT batch
   ```

2. Extend `DinoPreprocessSettings` with `encode_batch_size: int = Field(ge=1)` (or equivalent validation ≥ 1). No magic numbers in call sites — read from settings.

### A2. Encoder API (`dino_encoder.py`)

1. Add `encode_images(paths: Sequence[str]) -> list[list[float] | None]`:
   - Return length == `len(paths)`.
   - Chunk by `database.dino.encode_batch_size` (or an optional ctor/override if CLI passes a size).
   - **Fail rule (locked):** preprocess each path alone; stack only OK tensors; on batched ORT error → serial fallback for that micro-batch’s OK items; mark failed indices `None` — never poison siblings.
   - Keep L2-normalize / dim checks per vector as today.
2. Refactor `encode_image` to batch-of-1 semantics: on `None` / failure **raise** (preserve current exception types: `FileNotFoundError`, `RuntimeError`, …) so existing single-call sites keep working.
3. Optional: factor `_preprocess` → single-image CHW without batch dim, then stack for NCHW — keep code clear; do not change ImageNet mean/std/size.

### A3. Import wiring (`import_catalog.py`)

1. Replace per-row `encoder.encode_image` with a buffered / chunked path that calls `encode_images` for up to `encode_batch_size` pending rows that reached the encode step (after image copy / crop resolution).
2. For each `None` embedding: same counters/logs as today’s encode skip (`skipped_encode`); remove copied static file if that was done before encode (match current behavior).
3. Progress logs (`progress-every`) must still make sense with chunking.
4. Nice-to-have CLI: `--encode-batch-size N` overrides YAML for the run; document in manuals if added.
5. Full ~2k re-encode **not** required for handoff. Optional: note wall-clock vs serial in progress if you run a timing smoke.

---

## B. OPT-002 — YOLO `cropper.device`

### B1. Config + settings

1. In `config/compute_cropper.yaml` under `cropper:`, add:

   ```yaml
   device: cpu   # cpu | cuda | auto — YOLO ORT only; default cpu (online-safe)
   ```

2. Update the comment on `compute.device` — it is PHOCR+DINO only; YOLO uses `cropper.device`.

3. Extend `CropperSettings` with `device: str` and validator: must be `cpu` | `cuda` | `auto` (case-insensitive normalize OK).

### B2. Provider selection (`onnx_yolo.py`)

1. Rewrite `select_yolo_onnx_providers` to respect `device` like `select_dino_onnx_providers`, plus **`auto`** = CUDA if available else CPU. Stop ignoring `device` / `available`.
2. `OnnxYoloCropper.__init__`: call `select_yolo_onnx_providers(settings.cropper.device)` (not `settings.compute.device`).
3. Update class docstring / module comments: YOLO is **not** always CPU; default config is CPU.
4. `create_label_cropper` — no API change required if settings carry `cropper.device`.
5. Online path (`api/runtime.py`) needs **no** special case if YAML default is `cpu`.
6. Nice-to-have CLI on import: `--cropper-device {cpu,cuda,auto}` for `--crop-first` runs; apply before creating cropper (override settings copy or pass providers). Document if added.

### B3. No YOLO batching

Do not add multi-image YOLO encode/crop APIs.

---

## C. Manuals (Russian) — required

Update in the same change:

1. **`manuals/architecture.md`**
   - YOLO may use `cropper.device` (cpu|cuda|auto); default cpu.
   - Catalog import DINO encode may batch via `dino.encode_batch_size`.
   - Replace “ONNX Runtime — YOLO (CPU)” with accurate wording.

2. **`manuals/configuration_guide.md`**
   - Document `dino.encode_batch_size` in `database.yaml`.
   - Document `cropper.device` in `compute_cropper.yaml`.
   - Remove “YOLO always CPU EP (отдельного флага нет)”.
   - VRAM caveat: YOLO+PHOCR+DINO all on GPU can OOM; keep YOLO cpu for online eval; cuda YOLO OK for bulk crop-only.

3. **`manuals/quickstart.md`**
   - Remove “YOLO-кроппер пока всегда CPU”.
   - Note: bulk `--crop-first` may set `cropper.device: cuda` (or CLI); encode uses `encode_batch_size`.
   - Keep CPU/GPU sync guidance for `compute.device` / `requirements-gpu.txt`.

4. Sync **`manuals/index.md`** only if TOC/links need it.

---

## Out of scope

- YOLO N-batch
- VEC / RERANK tickets
- Mandatory full catalog reimport / owner_eval
- New packages
- Changing default online YOLO off CPU

---

## Acceptance

- [ ] `encode_images` + import uses `dino.encode_batch_size`; size `1` behaves like serial
- [ ] One bad image in a micro-batch does not fail siblings
- [ ] `cropper.device` selects YOLO EP; YAML default `cpu`; `compute.device` unchanged for PHOCR/DINO
- [ ] Manuals updated (RU); no “YOLO always CPU”
- [ ] Lint gate green on changed Python

---

## Verification (Coder, before handoff)

```bash
uv run ruff check src/
uv run bandit -r src/ -ll
# optional unit smoke if you add temporary local checks — prefer leave tests to @Tester
# optional: short encode of a few paths with encode_batch_size=4 vs 1 (timing note in progress)
```

Do **not** require full 2k re-encode for handoff.

---

## Handoff

Append to `agent_docs/progress/stage_2.md`:

```
STATUS: READY_FOR_TEST (OPT-001 / OPT-002)
```

→ @Tester [`tester_opt_001_002.md`](tester_opt_001_002.md).
