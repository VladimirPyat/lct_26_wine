# Backlog (post–Stage 2)

Открытые улучшения вне текущих инструкций. Не блокируют сдачу ядра.

---

## TICKET-OPT-001 — Batched DINO encode on catalog load

**Status:** OPEN  
**Priority:** later (bulk import / re-encode)  
**Context:** 2026-09-24 — GPU local path; catalog re-encode ~2k images.

### Current behavior

- `src/db/import_catalog.py` calls `encoder.encode_image(path)` **per row** (batch size 1).
- `DinoOnnxEncoder.encode_image` builds `NCHW` with `batch=1` and `session.run` once per image.
- No `encode_images(paths) -> list[vector]` / ORT batching.

### Desired

- When GPU is available, preprocess and run DINO in batches (configurable `encode_batch_size`, e.g. 8–32).
- CPU path may keep batch=1 or small batches.
- Import progress logs remain; skip/fail semantics unchanged (per-slug).

### Acceptance (when picked up)

- [ ] Batched API on encoder + wired in catalog import / crop-reencode
- [ ] Measurable wall-clock win on ~2k crops vs serial (document ratio)
- [ ] Config knob; manuals note

---

## TICKET-OPT-002 — Optional YOLO CUDA EP for bulk catalog crop

**Status:** OPEN  
**Priority:** later (bulk catalog crop pass)  
**Context:** 2026-09-24 — single-image CPU vs GPU negligible; ~2k catalog crops would benefit.

### Current behavior

- `select_yolo_onnx_providers` **always** returns `CPUExecutionProvider` (by design: VRAM shared with PHOCR on query path).
- `compute.device=cuda` affects PHOCR/DINO only; no cropper device flag.

### Desired

- Config switch, e.g. `cropper.device: cpu | cuda | auto` (or `cropper.use_cuda: bool`), default **cpu** for online eval (safe with PHOCR on GPU).
- Bulk catalog crop job (`--crop-first` / offline) may set `cuda` to speed ~2k images.
- Online `/v1/eval/predict` keeps YOLO on CPU unless explicitly overridden.

### Acceptance (when picked up)

- [ ] Provider selection respects cropper device flag
- [ ] Default online path unchanged (CPU YOLO)
- [ ] Document VRAM caveat when YOLO+OCR+DINO all on GPU
- [ ] Optional timing note on catalog crop pass

---

## Quality tickets (2026-09-24 owner_eval set1 ≈74% hit@1, recall@5≈85%)

| ID | File | Focus |
|----|------|--------|
| **TICKET-VEC-001** | [`../reports/ticket_vec_001_embedding_recall.md`](../reports/ticket_vec_001_embedding_recall.md) | Поднять vector recall / margin; дообучение без leakage на owner_eval |
| **TICKET-RERANK-001** | [`../reports/ticket_rerank_001_dino_shortlist.md`](../reports/ticket_rerank_001_dino_shortlist.md) | Rerank hurt на near-duplicates; калибровка под DINO (не SIFT) |

## Related (done / not tickets)

- Query OCR on GPU + `requirements-gpu.txt` / `LD_LIBRARY_PATH` — done locally 2026-09-24.
- Catalog vector = YOLO crop (not full bottle) — `fix_catalog_yolo_encode.md` (FIXED).
