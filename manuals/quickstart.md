# Быстрый запуск

Как поднять окружение и проверить, что система жива. Детали архитектуры и конфигов — в соседних мануалах.

**Статус:** начальное наполнение Stage 0; уточняет @Coder при смене Docker/compose/скриптов запуска.

## Зависимости

```bash
uv sync
```

## База данных

```bash
docker compose up -d
docker compose ps
```

Скопируйте [`.env.example`](../.env.example) в `.env` для `DATABASE_URL` (приложение на хосте → `127.0.0.1:5432`).

## API (заготовка)

```bash
uv run uvicorn api.main:app --app-dir src --reload --host 0.0.0.0 --port 8080
```

Проверка: `GET http://127.0.0.1:8080/health`

## CPU / GPU

`compute.device: cpu | cuda` в config (ORT execution providers). Postgres всегда на CPU.

## Eval harness (позже)

Эндпоинт `/v1/eval/predict` — Stage 2. Скрипт: `data/owner_eval/1/participant_test.sh` (см. README / этапы).
