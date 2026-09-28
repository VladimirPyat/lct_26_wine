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

## Pre-final rebuild (2026-09-28)

| ID | File | Status |
|----|------|--------|
| **REBUILD-FINAL-001** | — | OPEN — перед финалом: одна модель для индекса и запросов + полная пересборка |

**Context:** SigLIP fp16 (`siglip2_wine_p1_epoch_3_fp16.onnx`, 817 MiB vs 1.6 GiB fp32) прошёл Colab-гейт
(Dev-A/Dev-B R@1/R@5/MRR = fp32, ни один запрос не просел; cos vs fp32 min 0.99959).
Отчёт: Drive `_models_v4_siglip/siglip2_wine_p1_epoch_3_fp16_check.json`; ноутбук
[`../drafts/dino_train/onnx_fp16_siglip.ipynb`](../drafts/dino_train/onnx_fp16_siglip.ipynb).
Смешанный режим (индекс fp32 + запросы fp16) допустим временно — сдвиг скоров ~1e-3 ≪ min margin 0.011.

- [ ] `bin/siglip2_wine_p1_epoch_3_fp16.onnx` + `_preprocess.json` скачаны
- [ ] (опц.) `owner_eval` 1+2 с YOLO-кропом: fp16 ≥ fp32 (команда — последняя ячейка ноутбука)
- [ ] `config/database.yaml`: `dino_model_path` → fp16 (`embedding_dim` 1152 без изменений)
- [ ] Каталог: cleared CSV + фото из `data/owner_database/images` (51 фото «нет страницы на сайте»; 23 чужих фото без эмбеддинга)
- [ ] Пересборка БД/эмбеддингов каталога той же моделью (`scripts/rebuild_catalog_db.sh`)
- [ ] Train/eval-каталог: dedup только по файлам из CSV (сейчас выживает `shyopot-tsvetov-...-109` с фото «Ветер в травах» → `a0c040fc` gt_missing)
- [ ] Прогон `owner_eval` 1+2 через API, сверка с golden (set2 `750a209e` уже исправлен на розовое)

## Runtime profiles (2026-09-28)

| ID | File | Status |
|----|------|--------|
| **CFG-DEVICE-001** | — | OPEN, low priority — разделить конфигурации GPU / CPU (основа сейчас GPU; CPU работает, лишние зависимости некритичны) |

**Context:** замеры 2026-09-28 (медианы на запрос): GPU ≈150 мс без OCR (encode ~40 мс, PHOCR ~0.7 с);
CPU ≈1.1 с без OCR (encode SigLIP fp32 ~1 с, PHOCR 5–7 с). Сейчас режим только в YAML
(`compute.device` в `compute_cropper.yaml`, `ocr.engine` в `ocr_rerank.yaml`); пакеты: CPU = extra `ml`
(`onnxruntime`), GPU = overlay `requirements-gpu.txt` (`onnxruntime-gpu` + CUDA wheels).
Цепочка OCR «CUDA → PHOCR, нет CUDA → LLM, нет LLM → без OCR» — согласована отдельно (PROD-API follow-up:
`coder_product_api_fix1.md` FIX1-003, контракт `ocr_engine.md`); значение `auto` / env-override остаются здесь.

- [ ] `compute.device` / `ocr.engine`: значение `auto` (CUDA есть → cuda/phocr, иначе cpu/llm)
- [ ] env-override (напр. `VINE_DEVICE=cpu|cuda|auto`, `VINE_OCR_ENGINE`) поверх YAML; дефолты не меняются
- [ ] (опц., нужен ✅ на `pyproject.toml` + `uv.lock`) вынести `phocr` из `ml` в отдельный extra (`ocr-local`):
  тянет `datasets`/pyarrow/pandas, `onnx`, второй OpenCV — не нужен CPU-сборке с LLM OCR
- [ ] (опц.) int8-квантизация SigLIP для CPU (ожидаемо ×2–3; требует переимпорт каталога + `owner_eval`)
- [ ] `manuals/configuration_guide.md` + `quickstart.md`: профили GPU / CPU, команды установки

## Related (done / not tickets)

- Query OCR on GPU + `requirements-gpu.txt` / `LD_LIBRARY_PATH` — done locally 2026-09-24.
- Catalog vector = YOLO crop (not full bottle) — `fix_catalog_yolo_encode.md` (FIXED).
