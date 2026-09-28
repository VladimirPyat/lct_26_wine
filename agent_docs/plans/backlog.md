# Backlog (post–Stage 2)

Открытые улучшения вне текущих инструкций. Не блокируют сдачу ядра.

---

## TICKET-OPT-001 — Batched DINO encode on catalog load

**Status:** DONE (TEST_PASS 2026-09-25)  
**Report:** [`../reports/test_opt_001_002.md`](../reports/test_opt_001_002.md)  
**Plan / contract:** [`opt_001_002.md`](opt_001_002.md), [`../contracts/compute_opt.md`](../contracts/compute_opt.md)  
**Context:** GPU path; frequent re-encode. Shipped: `dino.encode_batch_size` (default 16) + `encode_images` + import buffering.

### Acceptance

- [x] Batched API on encoder + wired in catalog import
- [ ] Optional timing note on ~2k vs serial (skipped; not required)
- [x] Config knob + manuals

---

## TICKET-OPT-002 — Optional YOLO CUDA EP for bulk catalog crop

**Status:** DONE (TEST_PASS 2026-09-25)  
**Report:** [`../reports/test_opt_001_002.md`](../reports/test_opt_001_002.md)  
**Plan / contract:** [`opt_001_002.md`](opt_001_002.md), [`../contracts/compute_opt.md`](../contracts/compute_opt.md)  
**Context:** No YOLO N-batch. Shipped: `cropper.device: cpu|cuda|auto` (default **cpu**); bulk crop may set `cuda`.

### Acceptance

- [x] Provider selection respects `cropper.device`
- [x] Default online path unchanged (CPU YOLO)
- [x] VRAM caveat in manuals
- [ ] Optional timing note on catalog crop pass (skipped; not required)

---

## Quality tickets (2026-09-24 owner_eval set1 ≈74% hit@1, recall@5≈85%)

| ID | File | Focus |
|----|------|--------|
| **TICKET-VEC-001** | [`../reports/ticket_vec_001_embedding_recall.md`](../reports/ticket_vec_001_embedding_recall.md) | Поднять vector recall / margin; дообучение без leakage на owner_eval |
| **TICKET-RERANK-001** | [`../reports/ticket_rerank_001_dino_shortlist.md`](../reports/ticket_rerank_001_dino_shortlist.md) | Rerank hurt на near-duplicates; калибровка под DINO (не SIFT) |

## SigLIP2 switch (2026-09-27)

| ID | File | Status |
|----|------|--------|
| **SIG** | [`siglip_prod.md`](siglip_prod.md) | INSTRUCTIONS_READY — `coder_siglip_prod.md` / `tester_siglip_prod.md` |
| DATA-DEDUP-001 | — | Склеить дубли SKU (напр. `alma-valley-shardone-rezerv-beloe-suhoe-14` / `-135`) |
| SIG-ABS-001 | — | Калибровка `abs_min` под шкалу SigLIP (нужно для not-found gate Stage 3) |
| SIG-REF-001 | — | Рефакторинг имён `dino_*` → `encoder_*` |

## TZ gap review (2026-09-28)

| ID | File | Status |
|----|------|--------|
| **TZ-GAP-001** | [`../reports/ticket_tz_gap_001_remaining_scope.md`](../reports/ticket_tz_gap_001_remaining_scope.md) | OPEN — продуктовый API, F1 top-1/top-5, ARCHITECTURE.md, Docker, аналоги/сомелье, фронт |

## Product API + Web UI (2026-09-28)

| ID | File | Status |
|----|------|--------|
| **PROD-000 / PROD-API / WEB-UI** | [`web_product.md`](web_product.md) | INSTRUCTIONS_READY — PROD-000 on `master`, then parallel `feat/product-api` + `feat/web-ui` |

## Related (done / not tickets)

- Query OCR on GPU + `requirements-gpu.txt` / `LD_LIBRARY_PATH` — done locally 2026-09-24.
- Catalog vector = YOLO crop (not full bottle) — `fix_catalog_yolo_encode.md` (FIXED).
