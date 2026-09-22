# Postgres + pgvector: Compose и локальный доступ

## Цель

Одна БД: каталог вин (в т.ч. доп. поля и этикетки вне сайта) + вектор DINO (`vector(N)`).

Доступ:

1. Приложение **в Compose** → hostname `db`, порт 5432 внутри сети.  
2. Приложение **на хосте** (`uv run uvicorn`) → `localhost:5432` (published port).  
3. Опционально другие машины в LAN → тот же published port (осторожно с firewall).

## Черновик compose

```yaml
services:
  db:
    image: pgvector/pgvector:pg16   # или аналог
    environment:
      POSTGRES_USER: vine
      POSTGRES_PASSWORD: vine        # только dev; в .env
      POSTGRES_DB: vine
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U vine -d vine"]
      interval: 5s
      timeout: 5s
      retries: 10

  # app: optional later
  #   depends_on: { db: { condition: service_healthy } }
  #   environment:
  #     DATABASE_URL: postgresql+psycopg://vine:vine@db:5432/vine

volumes:
  pgdata:
```

## DATABASE_URL

| Режим | URL |
|-------|-----|
| App в compose | `postgresql+psycopg://vine:vine@db:5432/vine` |
| App на хосте | `postgresql+psycopg://vine:vine@127.0.0.1:5432/vine` |

Один ключ в `.env` / `app.yaml`; не хардкодить hostname в коде.

## Схема (эскиз)

- `wines`: slug UNIQUE, title, manufacturer, category, region, color, product_url, image_path, **extra JSONB**, embedding `vector(N)`  
- N = размер выхода DINO ONNX (зафиксировать при экспорте).  
- Индекс: `ivfflat` или `hnsw` по cosine/IP после загрузки каталога.

## CPU / GPU

К БД не относится. `compute.device` только для ORT EP (DINO/PHOCR). Postgres всегда CPU.

## Не делать на старте

- Отдельный FAISS-файл «на всякий случай» — дублирует источник правды.  
- Требовать GPU для поднятия БД.
