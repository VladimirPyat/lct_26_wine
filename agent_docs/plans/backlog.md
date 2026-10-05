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
- [x] (опц.) int8-квантизация SigLIP для CPU — сделано 2026-10-05 без переимпорта: запросы int8, каталог fp32
  (`scripts/quantize_encoder.py`, `bin/siglip2_wine_p1_epoch_3_int8.onnx`; см. `deploy_vps.md`)
- [x] профили конфигов `APP_ENV=dev|vps` (оверлеи `config/profiles/vps/`) — 2026-10-05, вместо env-override по ключам
- [ ] `manuals/configuration_guide.md` + `quickstart.md`: профили GPU / CPU, команды установки → TICKET-DEPLOY-001

## VPS deploy follow-ups (2026-10-05)

Plan: [`deploy_vps.md`](deploy_vps.md). Done (steps 1–4): profiles `APP_ENV=dev|vps` + encoder concurrency gate,
`Dockerfile` `VARIANT=cpu|gpu`, `docker-compose.vps.yml`, `.env.vps.example`, `scripts/deploy/{assets.lock,
fetch_assets.sh,restore_db_volume.sh,deploy_vps.sh}`. Local full-stack check: `/health` profile=vps,
owner_eval set 2 top-1 25/25, app RSS ≈1.13 GB, db ≈36 MB.

### TICKET-DEPLOY-001 — Manual: deploy on a fresh VPS

**Status:** DONE 2026-10-05 — `manuals/deploy_vps.md` (first real deploy passed; HTTPS → Caddy next)

- [ ] `manuals/deploy_vps.md` (RU): requirements (Ubuntu 22.04+/Debian 12, 2 vCPU / 4 GB, x86_64);
  Docker Engine + compose plugin — link to https://docs.docker.com/engine/install/ubuntu/ (+ post-install
  `usermod -aG docker`); optional 2 GB swap; firewall 22/80
- [ ] code: `git clone https://github.com/VladimirPyat/lct_26_wine.git /opt/vine` (public repo → HTTPS,
  no GitHub key on the server); if the repo becomes private → server-side read-only **deploy key**
  (`ssh-keygen -t ed25519`, add in repo Settings → Deploy keys), never copy a personal key
- [ ] secrets: `scp .env user@host:/opt/vine/.env` from the dev machine **or** `cp .env.vps.example .env` + edit;
  needs `QWEN_API_KEY`; `APP_ENV=vps` is forced by compose
- [ ] run `scripts/deploy/deploy_vps.sh`; check `curl http://<ip>/health` → `profile: vps`;
  optional `scripts/bench_encoder_cpu.py` latency on the real CPU
- [ ] update / rollback: `git pull && scripts/deploy/deploy_vps.sh`; new catalog → new `pgdata.tar.zst` +
  `assets.lock` + `deploy_vps.sh --yes` (backup volume `<vol>_bak_<ts>`; rollback via `VINE_PG_VOLUME`)
- [ ] how to cut a new DB archive locally (stop db → tar volume → zstd → sha256 → Drive → `assets.lock`);
  db image digest must match `docker-compose.vps.yml`
- [ ] retention cron for `scripts/cleanup_search_queries.py` (daily, inside app container)
- [ ] sync `manuals/index.md`, README link, `configuration_guide.md` (profiles section), `quickstart.md`

### TICKET-DEPLOY-002 — GitHub Actions: CI + one-button deploy

**Status:** deploy button DONE 2026-10-05 (`.github/workflows/deploy-vps.yml`: SSH → `git fetch` +
`checkout --detach <ref>` → `deploy_vps.sh`, image built on the server, no GHCR; secrets `VPS_HOST`,
`VPS_USER`, `VPS_SSH_KEY`, `VPS_KNOWN_HOSTS`, vars `VPS_PORT`, `VPS_APP_DIR`; setup in
`manuals/deploy_vps.md` §7). Open: `ci.yml`; GHCR build only if server-side build becomes a problem.

- [ ] `.github/workflows/ci.yml` (PR + push): `uv sync --extra ml --extra db --extra dev` → ruff → mypy → pytest;
  DB/model-dependent tests skipped when assets/Postgres absent (marker or service container)
- [ ] `.github/workflows/deploy.yml` (`workflow_dispatch` only; input `ref`):
  build `Dockerfile` `VARIANT=cpu` (buildx cache) → push `ghcr.io/vladimirpyat/lct_26_wine:sha-<short>` + `latest`
  → SSH to VPS: `git fetch && git checkout <ref> && VINE_IMAGE=ghcr.io/...:sha-<short> scripts/deploy/deploy_vps.sh`
  (compose `pull` instead of local build when `VINE_IMAGE` is a registry tag) → `/health`;
  on failure re-up previous tag (`data/tmp/deploy/state/current_tag`)
- [ ] secrets: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY` (dedicated deploy key pair: private in GitHub Secrets,
  public in server `~/.ssh/authorized_keys`); GHCR package public or read token on the VPS
- [ ] `deploy_vps.sh`: skip `--build` when `VINE_IMAGE` points to a registry (pull instead)

## Related (done / not tickets)

- Query OCR on GPU + `requirements-gpu.txt` / `LD_LIBRARY_PATH` — done locally 2026-09-24.
- Catalog vector = YOLO crop (not full bottle) — `fix_catalog_yolo_encode.md` (FIXED).
