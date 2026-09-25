# Быстрый запуск

Как поднять окружение, схему БД, каталог и eval API. Детали архитектуры и конфигов — в соседних мануалах.

**Статус:** Stage 2B — uvicorn + `POST /v1/eval/predict` + owner_eval set1.

## Зависимости

```bash
uv sync --extra ml --extra db --extra dev
```

Для локального OCR (`ocr.engine=phocr`) нужен пакет `phocr` в окружении (если отсутствует — см. `agent_docs/reports/BLOCKED.md` или временно `policy.enable_rerank: false` / `ocr.engine=llm`).

## База данных

```bash
docker compose up -d
docker compose ps   # healthy

cp .env.example .env   # если ещё нет
uv run alembic upgrade head
```

## Каталог (если ещё не загружен)

```bash
uv run python scripts/catalog_prepare/prepare_ready_csv.py
# Полный import с YOLO-кропами + wipe wines (вектор = этикетка, static = бутылка):
uv run python scripts/catalog_import.py --crop-first --recreate-wines
```

Флаги: `--crops-dir`, `--review-dir`, `--recreate-wines`, `--skip-crop-pass` (только encode из уже готовых кропов), `--limit N` (smoke).

Ожидаемо: число вин в БД ≈ число OK-кропов в `data/tmp/catalog_crops/`; `embedding IS NULL` = 0; review-only slug не вставляются; `static/wines/*.webp` — полные бутылки.

## API (eval)

```bash
uv run uvicorn api.main:app --app-dir src --host 0.0.0.0 --port 8080
```

- `GET /health` → `{"status":"ok"}`
- `GET /static/wines/{slug}.webp`
- `POST /v1/eval/predict` — multipart field **`image`** → `{"slug":"..."}`

Smoke:

```bash
curl -s -F "image=@./data/owner_eval/1/queries/04f3ce15.jpg" \
  http://127.0.0.1:8080/v1/eval/predict
```

## Owner eval set 1

API должен слушать `:8080`. Затем:

```bash
./data/owner_eval/1/participant_test.sh \
  --images-dir ./data/owner_eval/1/queries \
  --manifest ./data/owner_eval/1/queries.tsv \
  --endpoint 'http://127.0.0.1:8080/v1/eval/predict' \
  --output ./data/owner_eval/1/predictions.jsonl
```

Отчёт по decision log:

```bash
uv run python scripts/collect_eval_report.py \
  --log data/tmp/eval_decisions.jsonl \
  --predictions data/owner_eval/1/predictions.jsonl \
  --mapping data/owner_eval/1/mapping.json
```

Set 2 — те же пути под `data/owner_eval/2/`.

## CPU / GPU

Postgres всегда на CPU. Инференс (PHOCR / DINO) — через `compute.device` в `config/compute_cropper.yaml`. YOLO-кроппер пока всегда CPU (отдельного флага нет).

### По умолчанию — CPU (всегда рабочий путь)

```bash
uv sync --extra ml --extra db --extra dev   # колесо onnxruntime (CPU)
# config/compute_cropper.yaml → compute.device: cpu
```

Так и задумано для сервера заказчика: без GPU-пакетов всё должно подниматься. Если локально GPU «сломался» (нет драйвера / библиотек) — верните `device: cpu` и при необходимости снова `uv sync` (CPU-колесо).

### Опционально — локальный GPU (быстрее OCR)

Нужны NVIDIA-драйвер и overlay поверх venv (колёса `onnxruntime` и `onnxruntime-gpu` **несовместимы** в одном окружении):

```bash
uv pip uninstall onnxruntime
uv pip install -r requirements-gpu.txt
export LD_LIBRARY_PATH="$(pwd)/.venv/lib/python3.12/site-packages/nvidia/cu13/lib:$(pwd)/.venv/lib/python3.12/site-packages/nvidia/cudnn/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
# config/compute_cropper.yaml → compute.device: cuda
```

Без `LD_LIBRARY_PATH` CUDA EP может числиться, но не загрузиться — PHOCR с `use_cuda=True` тогда падает; безопасный откат: `device: cpu`. Детали и нюансы CUDA 12 vs 13 — в [configuration_guide.md](configuration_guide.md).

После обычного `uv sync --extra ml` CPU-колесо вернётся — для GPU снова поставьте overlay из `requirements-gpu.txt`.

## Policy без OCR (быстрый smoke)

В `config/ocr_rerank.yaml`: `policy.enable_rerank: false` — только YOLO→DINO→top-1, без PHOCR/LLM.
