# Быстрый запуск

Как поднять окружение, схему БД, подготовить CSV каталога и загрузить его в Postgres. Детали архитектуры и конфигов — в соседних мануалах.

**Статус:** Stage 1.2 — prepare CSV + import (DINO + `static/wines/`).

## Зависимости

```bash
uv sync --extra ml --extra db --extra dev
```

Pillow входит в extra `ml` (аудит размеров / prepare / копирование WebP).

## База данных

```bash
# 1. Поднять Postgres + pgvector
docker compose up -d
docker compose ps   # healthy

# 2. DATABASE_URL для приложения на хосте
cp .env.example .env   # если ещё нет (локально vine/vine — без секретов)

# 3. Схема + seed sweetness_levels
uv run alembic upgrade head
```

Проверка: таблицы `categories`, `regions`, `sweetness_levels`, `wines`; в `sweetness_levels` — 6 канонических значений.

## Подготовка CSV каталога

SSOT под `data/` **не меняется**. Артефакты пишутся в `scripts/catalog_prepare/`.

```bash
# (один раз) копия проблемного списка — уже может лежать в scripts/catalog_prepare/
# cp data/owner_database/wines_problem_images.csv scripts/catalog_prepare/

uv run python scripts/catalog_prepare/audit_image_sizes.py
uv run python scripts/catalog_prepare/prepare_ready_csv.py
```

Ожидаемо: `wines_ready.csv` (~1932), `wines_additional.csv` (~15–20), `wines_rejected.csv` (с колонкой `reason`).  
`MIN_SIDE=200`: ready — owner-картинка ≥ порога и уникальные имя фото / файл; additional — мелкий owner + site-rescue с уникальным content hash.

## Импорт в БД

```bash
uv run python scripts/catalog_import.py
# эквивалент: PYTHONPATH=src uv run python -m db.import_catalog
```

Флаги (опционально): `--limit N` (smoke), `--progress-every 50`, пути `--ready` / `--additional` / `--static-dir`.

Скрипт: get-or-create category/region; sweetness из site JSON `category` (exact token, longest first); копия в `static/wines/{slug}.webp`; DINO encode; `upsert_by_slug`. Пропуски (нет картинки / encode fail) — в лог, без INSERT.

Проверка:

```bash
# число вин и отсутствие пустых embedding / image_url
PYTHONPATH=src uv run python -c "
from sqlalchemy import text
from db.session import create_db_engine
e = create_db_engine()
with e.connect() as c:
    print(c.execute(text('select count(*) from wines')).scalar())
    print(c.execute(text(\"select count(*) from wines where embedding is null\")).scalar())
    print(c.execute(text(\"select count(*) from wines where image_url is null or image_url = ''\")).scalar())
"
ls static/wines/*.webp | wc -l
```

Индекс HNSW/IVFFlat по `embedding` после полной загрузки — опционально (follow-up); для Stage 1.2 не обязателен.

## API

```bash
uv run uvicorn api.main:app --app-dir src --reload --host 0.0.0.0 --port 8080
```

- `GET /health`
- каталожные картинки: `GET /static/wines/{slug}.webp` (mount FastAPI)

## CPU / GPU

`compute.device: cpu | cuda` в `config/compute_cropper.yaml` (ORT). Postgres всегда на CPU.

## Eval harness (позже)

Эндпоинт `/v1/eval/predict` — Stage 2. Скрипт: `data/owner_eval/1/participant_test.sh`.
