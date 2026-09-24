# Архитектура

Краткое описание компонентов, границ модулей и потоков данных. Не дублирует контракты и списки классов.

**Статус:** Stage 1.2 — prepare → import → DINO → pgvector.

## Компоненты

| Компонент | Назначение |
|-----------|------------|
| `api` (FastAPI) | HTTP-вход; `/health`, mount `/static/wines` |
| `core` | Конфиг YAML, cropper/OCR/text; `core/retrieve` — DINO ONNX |
| `db` | SQLAlchemy-модели + `WineRepository`; CLI `scripts/catalog_import.py` |
| `scripts/catalog_prepare/` | Аудит размеров + split ready/additional/rejected |
| Postgres (Compose) | Единая БД каталога и векторов DINO (`pgvector`) |
| `static/wines/` | Публичные изображения каталога (`image_url`) |
| `bin/*.onnx` | YOLO cropper, DINO (`dinov2_wine_final.onnx` + `.onnx.data`) |

Lookup-таблицы: `categories`, `regions`, `sweetness_levels`.  
Таблица `wines`: метаданные, `dishes TEXT[]`, `embedding vector(N)` (N из `config/database.yaml`).

## Поток данных каталога (Stage 1.2)

```
data/owner_database + data/site_database   (SSOT, read-only)
        │
        ▼
scripts/catalog_prepare/prepare_ready_csv.py
        │  MIN_SIDE=200, JSON enrich (rating/temp/alcohol/dishes)
        ▼
wines_ready.csv + wines_additional.csv (+ rejected on disk)
        │
        ▼
python scripts/catalog_import.py
        ├─ category/region get-or-create (empty → «н/д»)
        ├─ sweetness_id ← site JSON category tokens
        ├─ copy → static/wines/{slug}.webp
        ├─ DinoOnnxEncoder.encode_image
        └─ WineRepository.upsert_by_slug
        ▼
Postgres wines.embedding + image_url
```

Rejected CSV не импортируется в первом прогоне (файлы для ручных правок).

## Границы слоёв (retrieve)

```
image path
  → core.retrieve.encode_image / DinoOnnxEncoder   # вне репозитория
  → db.WineRepository.search_by_embedding          # только вектор top-K
  → list[RankedHit]                                # score = 1 − cosine_distance
```

- **Encoder** (`src/core/retrieve/`): preprocess (resize 224, ImageNet mean/std), ORT-инференс, L2-нормализация `pooler_output`.
- **Repository** (`src/db/repository.py`): CRUD по id, slug/upsert, `get_many_by_ids`, `search_filters` (AND). **Не** комбинирует vector ORDER BY с фильтрами в одном SQL.
- **RankedHit.image_path** ← `wines.image_url`.

## Pipeline / этапы обработки (поиск, позже)

```
image → YOLO crop → DINO embed → retrieve (pgvector) → OCR rerank / policy → response
```

Для каталожных кадров YOLO опционален: encode полного кадра бутылки.

## Внешние зависимости

- **Postgres 16 + pgvector** — `docker compose` (`pgvector/pgvector:pg16`), том `pgdata`
- **Alembic** — миграции в `alembic/versions/`
- **ONNX Runtime** + **Pillow** — инференс и prepare (extra `ml`)
- Картинки-источники: `data/owner_database/`, `data/site_database/` (не в git)
