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
uv run python scripts/catalog_import.py
```

Ожидаемо ~1950 вин с непустым `embedding` и файлами в `static/wines/`.

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

`compute.device: cpu | cuda` в `config/compute_cropper.yaml`. Postgres всегда на CPU.

## Policy без OCR (быстрый smoke)

В `config/ocr_rerank.yaml`: `policy.enable_rerank: false` — только YOLO→DINO→top-1, без PHOCR/LLM.
