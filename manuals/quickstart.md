# Быстрый запуск

Как поднять окружение, схему БД, каталог и eval API. Детали архитектуры и конфигов — в соседних мануалах.

**Статус:** Stage 2B — uvicorn + `POST /v1/eval/predict` + owner_eval set1; Stage 3 — продуктовый API `/api/v1/*`.

## Зависимости

```bash
uv sync --extra ml --extra db --extra dev
```

Для локального OCR (`ocr.engine=phocr`) нужен пакет `phocr` в окружении (если отсутствует — см. `agent_docs/reports/BLOCKED.md` или временно `policy.enable_rerank: false` / `ocr.engine=llm`).

## Модели в `bin/`

Файлы не в git — положить вручную:

- `bin/siglip2_wine_p1_epoch_3.onnx` — энкодер изображений (выход 1152);
- `bin/siglip2_wine_p1_epoch_3_preprocess.json` — параметры препроцесса обучения (сверка с `config/database.yaml`);
- `bin/yolo_detect_labels_2.onnx` — YOLO-детектор этикетки.

Если размерность ONNX не совпадает с `embedding_dim`, API и импорт падают при старте с понятной ошибкой.

## База данных

```bash
docker compose up -d
docker compose ps   # healthy

cp .env.example .env   # если ещё нет
uv run alembic upgrade head
```

На свежей БД `0001` сразу создаёт `vector(1152)`, `0002` — no-op. На БД, где каталог уже залит DINO (768), `alembic upgrade head` откажется работать — см. «Перезаливка каталога».

## Каталог (если ещё не загружен)

```bash
uv run python scripts/catalog_prepare/prepare_ready_csv.py
# Полный import с YOLO-кропами + wipe wines (вектор = этикетка, static = бутылка):
uv run python scripts/catalog_import.py --crop-first --recreate-wines
```

Флаги: `--csv PATH` (повторяемый, заменяет ready/additional), `--clean-images`, `--crops-dir`, `--review-dir`, `--recreate-wines`, `--skip-crop-pass` (только encode из уже готовых кропов), `--limit N` (smoke).

## Перезаливка каталога (смена энкодера / очищенный CSV)

Источник — CSV владельца (`data/owner_database/wines_integrated_updated.csv`) и фото `data/owner_database/images/{slug}.webp`. **Удаляет все строки `wines`.**

В БД идут эмбеддинги **кропов этикетки** (`data/tmp/catalog_crops/`), в статику — **полные бутылки** (`static/wines/`). Оба набора строятся из одного исходника на slug; вино без OK-кропа не попадает ни в статику, ни в БД (карантин `data/tmp/catalog_crops_review/reasons.csv`).

```bash
# 1. Подготовка без БД: CSV → старые ассеты в .trash/ → YOLO-кропы + статика → сверка
scripts/rebuild_catalog_db.sh --prepare-only
#    сверка: scripts/catalog_prepare/verify_catalog_assets.py → data/tmp/catalog_assets_check.csv
#    (кроп ⇔ статика, статика == исходник, кроп найден внутри статики по пикселям)

# 2. БД на уже подготовленных ассетах: VINE_RESET_EMBEDDINGS=1 alembic upgrade head → encode + import
docker compose up -d
scripts/rebuild_catalog_db.sh --yes --reuse-assets
# всё сразу (1 + 2):
scripts/rebuild_catalog_db.sh --yes -- --encode-batch-size 16
```

То же вручную:

```bash
uv run python scripts/catalog_prepare/prepare_clean_csv.py
uv run python scripts/catalog_import.py \
  --csv scripts/catalog_prepare/wines_clean_ready.csv --crop-first --assets-only
uv run python scripts/catalog_prepare/verify_catalog_assets.py
VINE_RESET_EMBEDDINGS=1 uv run alembic upgrade head
uv run python scripts/catalog_import.py \
  --csv scripts/catalog_prepare/wines_clean_ready.csv --skip-crop-pass --recreate-wines
```

Проверка: `SELECT count(*), count(embedding) FROM wines;` и
`SELECT atttypmod FROM pg_attribute WHERE attrelid = 'wines'::regclass AND attname = 'embedding';` → `1152`.

Откат на DINO: вернуть закомментированный DINO-блок в `config/database.yaml`, положить его ONNX в `bin/`, повторить перезаливку.

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

## Продуктовый API (`/api/v1`)

Тот же uvicorn. Пороги и лимиты — `config/product.yaml` (см. [configuration_guide.md](configuration_guide.md)).

| Метод / путь | Ответ |
|---|---|
| `POST /api/v1/search` (multipart **`image`**) | `SearchResult`: `search_id`, `status` (`found` / `low` / `not_found`), `confidence_level`, `winner`, `candidates` (top-5), `analogs` |
| `GET /api/v1/search/{search_id}` | сохранённый `SearchResult` |
| `GET /api/v1/search/{search_id}/analogs?limit=5` | `AnalogsResult` (`winner_filters` / `ocr_filters` / `vector`) |
| `GET /api/v1/wines/{slug}` | `WineCard` |
| `GET /api/v1/wines?color=&grape=&region=&sweetness=&dish=&exclude_manufacturer=&limit=5&offset=0` | `{"items": [...], "total": N}` |
| `GET /api/v1/dictionaries` | цвета, сорта, регионы, сладость, блюда |
| `POST /api/v1/feedback` (JSON) | 204 |

Ошибки — `{"detail": "..."}`: 400 пустой / недекодируемый файл, 413 больше `upload.max_mb`, 415 тип не из `upload.content_types`, 422 неверные параметры, 404 нет поиска / вина, 503 пустой каталог.

```bash
B=http://127.0.0.1:8080/api/v1
curl -s -F "image=@./data/owner_eval/1/queries/26ddb066.jpg" $B/search | tee /tmp/search.json
SID=$(python3 -c "import json; print(json.load(open('/tmp/search.json'))['search_id'])")
curl -s $B/search/$SID
curl -s "$B/search/$SID/analogs?limit=5"
curl -s -G $B/wines --data-urlencode color=Красное --data-urlencode grape=Саперави --data-urlencode limit=3
curl -s $B/wines/agora-muskat-chernyj
curl -s $B/dictionaries
curl -s -o /dev/null -w "%{http_code}\n" -H 'Content-Type: application/json' \
  -d "{\"search_id\":\"$SID\",\"verdict\":\"match\"}" $B/feedback      # 204
```

Фото запросов и JSON результатов — `data/tmp/search_queries/` (10 дней), отзывы — `data/tmp/search_feedback.jsonl`. Чистка по сроку — при старте и `uv run python scripts/cleanup_search_queries.py [--dry-run] [--days N]`.

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

Postgres всегда на CPU. Инференс PHOCR / SigLIP2 — через `compute.device` в `config/compute_cropper.yaml`. YOLO — отдельно через `cropper.device` (`cpu` \| `cuda` \| `auto`, default **`cpu`** для online-safe). Bulk `--crop-first` может задать `cropper.device: cuda` или CLI `--cropper-device`; catalog encode батчится через `dino.encode_batch_size` / `--encode-batch-size`.

### По умолчанию — CPU (всегда рабочий путь)

```bash
uv sync --extra ml --extra db --extra dev   # колесо onnxruntime (CPU)
# config/compute_cropper.yaml → compute.device: cpu, cropper.device: cpu
```

Так и задумано для сервера заказчика: без GPU-пакетов всё должно подниматься. Если локально GPU «сломался» (нет драйвера / библиотек) — верните `compute.device: cpu` (и при необходимости `cropper.device: cpu`) и снова `uv sync` (CPU-колесо).

### Опционально — локальный GPU (быстрее OCR / SigLIP2)

SigLIP2 so400m заметно тяжелее DINOv2-base: полный реимпорт каталога на CPU идёт долго, на GPU — в разы быстрее. Замеры и нюансы ORT CUDA — `agent_docs/reports/siglip2_embedding_results.md`.

Нужны NVIDIA-драйвер и overlay поверх venv (колёса `onnxruntime` и `onnxruntime-gpu` **несовместимы** в одном окружении):

```bash
uv pip uninstall onnxruntime
uv pip install -r requirements-gpu.txt
export LD_LIBRARY_PATH="$(pwd)/.venv/lib/python3.12/site-packages/nvidia/cu13/lib:$(pwd)/.venv/lib/python3.12/site-packages/nvidia/cudnn/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
# config/compute_cropper.yaml → compute.device: cuda
# cropper.device: cpu  (рекомендуется для online; cuda — для bulk crop-only)
```

Без `LD_LIBRARY_PATH` CUDA EP может числиться, но не загрузиться — PHOCR с `use_cuda=True` тогда падает; безопасный откат: `compute.device: cpu`. Детали и нюансы CUDA 12 vs 13 — в [configuration_guide.md](configuration_guide.md).

После обычного `uv sync --extra ml` CPU-колесо вернётся — для GPU снова поставьте overlay из `requirements-gpu.txt`.

## Policy без OCR (быстрый smoke)

В `config/ocr_rerank.yaml`: `policy.enable_rerank: false` — только YOLO→SigLIP2→top-1, без PHOCR/LLM.
