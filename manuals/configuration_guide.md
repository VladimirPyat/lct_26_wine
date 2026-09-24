# Руководство по конфигурации

Зачем и когда менять настройки (профили, YAML, режимы запуска). Полные схемы ключей — в `agent_docs/contracts/`, не здесь.

**Статус:** Stage 1.2 — пути каталога, `MIN_SIDE`, static, флаги import.

## Где лежат настройки

| Источник | Что задаёт |
|----------|------------|
| `.env` (копия с `.env.example`) | `DATABASE_URL` — единственный способ указать хост БД |
| `config/database.yaml` | `dino_model_path`, `embedding_dim`, блок `dino` (resize/normalize/L2) |
| `config/compute_cropper.yaml` | `compute.device` / threads (ORT для DINO и др.), YOLO cropper |
| `config/ocr_rerank.yaml` | OCR / fuzzy / rerank |
| `docker-compose.yml` | сервис `db`, порт `5432`, том `pgdata` |
| Константа prepare | `MIN_SIDE = 200` в `scripts/catalog_prepare/image_audit.py` |

## Пути данных каталога

| Путь | Роль |
|------|------|
| `data/owner_database/wines_integrated_updated.csv` | Owner truth (SSOT, read-only) |
| `data/owner_database/images/` | Owner `.webp` |
| `data/owner_database/wines_problem_images.csv` | Аудит-подсказка; копия в `scripts/catalog_prepare/` |
| `data/site_database/wines_database_enriched.json` | Enrich по slug + sweetness token |
| `data/site_database/images/` | Site images для additional |
| `scripts/catalog_prepare/` | Выход prepare (`wines_ready/additional/rejected`) |
| `static/wines/` | Публичные файлы после import (`image_url=/static/wines/{slug}.webp`) |

Бинарники в `static/wines/*` в gitignore; остаётся `.gitkeep`.

## Типовые сценарии

### Локальная БД (приложение на хосте)

1. `docker compose up -d`
2. `.env` с  
   `DATABASE_URL=postgresql+psycopg://vine:vine@127.0.0.1:5432/vine`
3. `uv run alembic upgrade head`

### Приложение внутри Compose-сети

В URL hostname `db` вместо `127.0.0.1` (см. комментарий в `.env.example`).

### Prepare: порог размера

- `MIN_SIDE=200` — `min(width, height)` через Pillow.
- Менять только осознанно и согласованно с контрактом `catalog_prepare.md` (и перегенерировать CSV).

### Import: флаги CLI

`uv run python scripts/catalog_import.py` (или `PYTHONPATH=src uv run python -m db.import_catalog`):

| Флаг | Назначение |
|------|------------|
| `--ready` / `--additional` | Пути к CSV (по умолчанию `scripts/catalog_prepare/…`) |
| `--owner-images` / `--site-images` | Корни исходных картинок |
| `--site-json` | JSON для match sweetness по `category` |
| `--static-dir` | Куда писать `{slug}.webp` |
| `--progress-every` | Лог прогресса (default 50) |
| `--limit` | Ограничить число строк (smoke) |

Sweetness: case-insensitive exact token по site `category`, longest first (`экстра брют` перед `брют`); иначе `sweetness_id` NULL.  
Пустые текстовые поля owner → sentinel `н/д`.

### DINO encode (путь, размерность, device)

1. Веса: `bin/dinov2_wine_final.onnx` (+ sidecar `.onnx.data`); путь — `dino_model_path` в `database.yaml`.
2. Размерность колонки и выхода: `embedding_dim` (проба `pooler_output`).
3. Preprocess в `database.yaml` → `dino`: `input_size` (224), ImageNet `normalize_mean` / `normalize_std`, `l2_normalize`.
4. Device/threads: `compute.device` (`cpu` \| `cuda`) и `ort_threads` в `compute_cropper.yaml`.

Менять preprocess только вместе с переэкспортом ONNX — иначе каталог и query «разъедутся».

### Смена размерности эмбеддинга

1. Переэкспорт / смена DINO ONNX → снова прозондировать выход `pooler_output`.
2. Обновить `embedding_dim` в `config/database.yaml`.
3. Новая Alembic-миграция на тип `vector(N)` (смена N ломает существующие строки).

### CPU / GPU для моделей

`compute.device: cpu | cuda` в `compute_cropper.yaml` — только ORT (DINO; PHOCR позже). Postgres всегда CPU.

## Чего здесь нет

- Секреты и реальные `.env` значения
- Полный перечень ключей (см. контракты `wines_schema.md`, `catalog_prepare.md`, `wines_repository.md`)
