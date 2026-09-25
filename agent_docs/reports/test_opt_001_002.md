# Test report — OPT-001 / OPT-002 (compute opt)

**Date:** 2026-09-25  
**Instructions:** `agent_docs/instructions/tester_opt_001_002.md`  
**Contract:** `agent_docs/contracts/compute_opt.md`  
**Verdict:** **PASS**

## Commands

| Command | Exit code | Result |
|---------|-----------|--------|
| `uv run pytest tests/ -v -k "compute_opt or dino_batch or yolo_provider or encode_batch or cropper_device"` | 0 | **15 passed**, 32 deselected |
| `uv run ruff check src/ tests/` | 0 | All checks passed |

No full catalog reimport / owner_eval (out of scope per instructions).

## Unit cases vs `tester_opt_001_002.md`

### OPT-001 — DINO batch

| Case | Test | Result |
|------|------|--------|
| `encode_batch_size` from YAML (default ≥ 1) | `test_encode_batch_size_loads_from_yaml` | PASS (16) |
| Reject 0 (validator) | `test_encode_batch_size_rejects_zero`, `test_dino_encoder_ctor_rejects_encode_batch_size_below_one` | PASS |
| `encode_images` length == input | `test_encode_images_return_length_matches_input` | PASS |
| Missing path → `None`, siblings OK | `test_encode_images_missing_path_none_siblings_ok` | PASS |
| Serial fallback on batched ORT error | `test_encode_images_serial_fallback_on_batched_ort_error` | PASS |
| `encode_image` raises on missing file | `test_encode_image_raises_on_missing_file` | PASS |
| Batch size 1 does not crash | `test_encode_images_batch_size_one_ok` | PASS |

### OPT-002 — YOLO providers

| Case | Test | Result |
|------|------|--------|
| `cpu` → CPU only (CUDA available) | `test_select_yolo_providers_cpu_only` | PASS |
| `cuda` + CUDA → `[CUDA, CPU]` | `test_select_yolo_providers_cuda_with_cuda` | PASS |
| `cuda` without CUDA → CPU + warning | `test_select_yolo_providers_cuda_without_cuda` | PASS |
| `auto` with/without CUDA | `test_select_yolo_providers_auto_with_and_without_cuda` | PASS |
| Default YAML `cropper.device == cpu` | `test_default_yaml_cropper_device_is_cpu` | PASS |
| Uses `cropper.device` not `compute.device` | `test_cropper_uses_cropper_device_not_compute` | PASS |
| Invalid device rejected | `test_cropper_device_rejects_unknown` | PASS |

Optional real ONNX smoke (2–4 images): **not run** (not blocking; ORT mocked).

## Manuals checklist

| File | Check | Result |
|------|-------|--------|
| `manuals/architecture.md` | YOLO via `cropper.device`; DINO batch mentioned | OK |
| `manuals/configuration_guide.md` | Both keys + VRAM caveat | OK |
| `manuals/quickstart.md` | No “YOLO всегда CPU”; bulk cuda + encode batch | OK |
| `manuals/index.md` | TOC unchanged (no new manual) | OK / N/A |

## Artifacts

- `tests/test_compute_opt.py` — 15 unit tests (mocked ORT; YAML load for defaults)

## Defects

None (blocking or non-blocking).

## Next

OPT-001 / OPT-002 sign-off OK. No @Coder follow-up required from this pass.
