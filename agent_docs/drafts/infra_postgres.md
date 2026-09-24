# Postgres + pgvector: Compose и локальный доступ

## Цель

Одна БД: каталог вин + вектор DINO (`vector(N)`). Схема: [`../contracts/wines_schema.md`](../contracts/wines_schema.md).

Доступ:

1. Приложение **в Compose** → hostname `db`, порт 5432 внутри сети.  
2. Приложение **на хосте** (`uv run uvicorn`) → `localhost:5432` (published port).  

## Compose

См. корневой `docker-compose.yml` (`pgvector/pgvector:pg16`, том `pgdata`, user/db `vine`).

## DATABASE_URL

| Режим | URL |
|-------|-----|
| App в compose | `postgresql+psycopg://vine:vine@db:5432/vine` |
| App на хосте | `postgresql+psycopg://vine:vine@127.0.0.1:5432/vine` |

Ключ в `.env` (копия с `.env.example`). Не хардкодить hostname в коде.

## Схема

См. контракт `wines_schema.md`: `categories`, `regions`, `sweetness_levels`, `wines` (+ `embedding vector(N)`).

Индекс HNSW/IVFFlat — после первой полной загрузки каталога.

## CPU / GPU

К БД не относится. `compute.device` только для ORT (DINO/YOLO/PHOCR).

## Не делать

- Отдельный FAISS-файл как второй источник правды.  
- Папка `db/` для векторов на диске — не нужна (векторы в `pgdata`).
