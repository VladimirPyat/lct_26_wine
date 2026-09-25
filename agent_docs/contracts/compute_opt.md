# Contract — Compute optimizations (OPT-001 / OPT-002)

**Status:** approved (user 2026-09-25) — Phase B instructions ready.  
**Tickets:** OPT-001 (DINO batch encode), OPT-002 (optional YOLO CUDA EP).  
**Priority:** OPT-001 first, then OPT-002.  
**No new packages.**

Related: `config/database.yaml`, `config/compute_cropper.yaml`, `src/core/retrieve/dino_encoder.py`, `src/core/cropper/onnx_yolo.py`, `src/db/import_catalog.py`, `src/core/config.py`.

---

## Out of scope

- YOLO N-image batching (crop stays one image per `session.run`)
- Quality tickets VEC / RERANK
- Changing `compute.device` semantics (still PHOCR + DINO only)
- New dependencies / lockfile changes

---

## OPT-001 — Batched DINO encode

### Config

| Key | File | Type | Default | Meaning |
|-----|------|------|---------|---------|
| `dino.encode_batch_size` | `config/database.yaml` under `dino:` | `int` ≥ 1 | `16` | Max images per ORT `session.run` during catalog encode / re-encode. `1` = serial (same wall behavior as today). |

Belongs with DINO preprocess (`DinoPreprocessSettings`), **not** under `compute:`.

Optional CLI (nice-to-have): `--encode-batch-size N` on catalog import overrides YAML for that run.

### API

| Method | Behavior |
|--------|----------|
| `encode_images(paths: Sequence[str]) -> list[list[float] \| None]` | Length always equals `len(paths)`. Index `i` is the vector or `None` if that path failed. |
| `encode_image(path) -> list[float]` | Equivalent to a batch of one: on failure **raise** (preserve current callers); on success return the vector. May delegate to `encode_images([path])`. |

Batching only stacks tensors that passed preprocess. Chunk size = `encode_batch_size`.

### Fail semantics (locked)

Per-slug skip stays unchanged at the import layer. Encoder rules:

1. **Preprocess individually** (read + resize + normalize). A bad path does **not** abort siblings: mark that index `None` (or raise only when using `encode_image`).
2. **ORT micro-batch** = stack of successfully preprocessed tensors only (order preserved relative to OK subset).
3. If the **batched** `session.run` raises → **fall back to serial** `session.run` for each OK tensor in that micro-batch. Individual serial failures → that original index `None` (or raise for `encode_image`).
4. Do **not** fail the entire micro-batch because one image is corrupt / missing / zero-norm.

Import / crop-reencode wiring must call `encode_images` in chunks (or buffer rows then encode), map `None` → same skip counters / logs as today’s per-row `encode_image` `except`.

### Device

Unchanged: DINO ORT providers from `compute.device` via existing `select_dino_onnx_providers`. Batching is orthogonal to GPU/CPU.

---

## OPT-002 — Optional YOLO CUDA EP

### Config

| Key | File | Type | Default | Meaning |
|-----|------|------|---------|---------|
| `cropper.device` | `config/compute_cropper.yaml` under `cropper:` | `cpu` \| `cuda` \| `auto` | **`cpu`** | ORT ExecutionProvider selection for YOLO only. Independent of `compute.device`. |

Optional CLI (nice-to-have): `--cropper-device {cpu,cuda,auto}` on import / `--crop-first` overrides YAML for that run.

### Provider selection

Mirror DINO style in `select_yolo_onnx_providers(device, *, available=...)`:

| `cropper.device` | Providers |
|------------------|-----------|
| `cpu` | `[CPUExecutionProvider]` |
| `cuda` | `[CUDAExecutionProvider, CPUExecutionProvider]` if CUDA EP listed in `available`; else warn + CPU |
| `auto` | CUDA pair if CUDA EP available, else CPU |

`OnnxYoloCropper` / `create_label_cropper` must pass **`settings.cropper.device`**, not `settings.compute.device`.

No YOLO multi-image batch API.

### Online vs bulk

| Path | Expected device |
|------|-----------------|
| Online `/v1/eval/predict` / default YAML | YOLO **CPU** (`cropper.device: cpu`) |
| Bulk catalog `--crop-first` | May set `cropper.device: cuda` (or CLI override) for ~2k crops |
| PHOCR + DINO | Still `compute.device` only |

### VRAM caveat (must document in manuals)

Running YOLO + PHOCR + DINO all on GPU can exhaust VRAM. Default keeps YOLO on CPU so online eval can share GPU with PHOCR/DINO. Bulk crop-only jobs may safely use CUDA YOLO when OCR is not loaded.

---

## Acceptance (both tickets)

- [ ] `encode_images` + import uses `dino.encode_batch_size`; `1` preserves serial semantics
- [ ] Bad image does not poison sibling encodes in a micro-batch
- [ ] `cropper.device` drives YOLO EP; default `cpu`; online path unchanged unless overridden
- [ ] No YOLO batching; no new deps
- [ ] Manuals: architecture / configuration_guide / quickstart updated (remove “YOLO always CPU”)
