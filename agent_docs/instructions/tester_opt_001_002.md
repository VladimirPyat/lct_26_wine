# @Tester — OPT-001 + OPT-002

**After:** @Coder finishes [`coder_opt_001_002.md`](coder_opt_001_002.md).  
**Contract:** [`../contracts/compute_opt.md`](../contracts/compute_opt.md)  
**Plan:** [`../plans/opt_001_002.md`](../plans/opt_001_002.md)

## Goal

Verify config knobs, provider selection, and batch-encode fail/shape semantics with **unit tests**. Confirm manuals no longer claim “YOLO always CPU”. **No** mandatory full catalog reimport or owner_eval.

---

## Setup

```bash
uv sync --extra ml --extra db --extra dev
# GPU overlay not required for unit tests (mock `available` providers)
```

---

## Unit tests to add (under `tests/`)

Prefer focused modules, e.g. `tests/test_compute_opt.py` or split `test_dino_batch.py` / `test_yolo_providers.py`. Mock ORT / avoid loading real heavy models when possible; if session load is required, use existing `bin/*.onnx` only for a tiny smoke and keep most tests pure.

### OPT-001 — DINO batch

- [ ] `encode_batch_size` loads from `DinoPreprocessSettings` / YAML (default ≥ 1; reject 0 if validator present).
- [ ] `encode_images` return length == input length.
- [ ] With a mock/session stub: one failing preprocess (missing path) → that index `None`, siblings still vectors (or serial-fallback path covered).
- [ ] `encode_image` still raises on missing file (compat).
- [ ] Batch size 1 path does not crash (serial equivalent).

### OPT-002 — YOLO providers

- [ ] `select_yolo_onnx_providers("cpu", available=[..., CUDA...])` → CPU only.
- [ ] `select_yolo_onnx_providers("cuda", available=[CUDA, CPU])` → `[CUDA, CPU]`.
- [ ] `select_yolo_onnx_providers("cuda", available=[CPU only])` → CPU (+ warning acceptable).
- [ ] `select_yolo_onnx_providers("auto", available=[CUDA, CPU])` → CUDA pair; without CUDA → CPU.
- [ ] Default YAML / settings: `cropper.device == "cpu"` (load `compute_cropper.yaml` or construct `CropperSettings` from fixture matching repo default).
- [ ] Cropper construction uses `cropper.device` not `compute.device` (e.g. compute=cuda + cropper=cpu → providers CPU-only when `available` includes CUDA).

### Smoke (optional, not blocking)

- Tiny real encode of 2–4 local images with `encode_batch_size=2` if environment has ORT+model — skip or mark optional if too heavy/CI-hostile.
- Do **not** require `--crop-first` on full catalog.

---

## Manuals check

- [ ] `manuals/architecture.md` — YOLO device via `cropper.device`; DINO batch on import mentioned.
- [ ] `manuals/configuration_guide.md` — both new keys documented; VRAM caveat present.
- [ ] `manuals/quickstart.md` — no “YOLO всегда CPU”; bulk crop cuda + encode batch noted.
- [ ] `manuals/index.md` consistent if TOC changed.

---

## Commands

```bash
uv run ruff check src/ tests/
uv run pytest tests/ -v -k "compute_opt or dino_batch or yolo_provider or encode_batch or cropper_device"
# or full:
uv run pytest tests/ -v
```

Record exact test names and pass/fail in the report.

---

## Out of scope

- Full 2k catalog re-encode / timing ratio gate
- owner_eval hit@1
- YOLO multi-image batch (must remain absent)
- VEC / RERANK

---

## Report + progress

Write `agent_docs/reports/test_opt_001_002.md` with:

- Commands + exit codes
- Which unit cases covered
- Manuals checklist
- Any defects (non-blocking vs blocking)

Append to `agent_docs/progress/stage_2.md`: `TEST_PASS` or `TEST_FAIL` (OPT-001/002) with link to the report.
