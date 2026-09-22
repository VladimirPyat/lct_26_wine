# Greenfield: сканер вин (ТЗ 2026)

**Статус:** план в `migration/` после решения не переписывать старый SIFT-проект.  
**Стек:** DINO (ONNX) + PostgreSQL/pgvector + PHOCR + fuzzy OCR-rerank + FastAPI.  
**Источник кода для переноса:** [`../MANIFEST.md`](../MANIFEST.md).  
**План по этапам:** [stages.md](stages.md).

## 1. Зафиксированные решения

| Тема | Решение |
|------|---------|
| Старый репо | не правим как основу; берём снимок в `migration/` |
| Retrieval | дообученный **DINO** → ONNX → top-K по cosine/IP в **pgvector** |
| Text | PHOCR + fuzzy (транслит, поля title/manufacturer/category) только как **rerank** шортлиста |
| SigLIP | не используем (нет времени на image–text пары; DINO уже дал целевую точность на малой выборке) |
| Выдача UI | одна карточка при достаточном отрыве; иначе OCR-rerank top-K; ниже порога — «не найдено» (+ аналоги — см. продукт) |
| Eval | `POST /v1/eval/predict`, multipart `image`, `{"slug":"..."}`; скрипт в `eval_organizer/` |
| Runtime deps | onnxruntime (± CUDA); без torch/transformers в сервисе |
| Модели | всё в `bin/`: YOLO, DINO ONNX, веса PHOCR |
| Каталог | новый дамп + доп. поля + этикетки вне сайта → Postgres |
| GPU | заказчик — GPU; тестовый сервер — CPU → `compute.device` |

## 2. Политика выдачи (ядро ТЗ)

Одна точка входа поиска (детали API позже), поведение:

1. DINO top-K из pgvector.  
2. Если отрыв top-1 vs top-2 **достаточный** (порог уточним) → сразу slug / одна карточка. OCR можно не ждать.  
3. Если несколько близких кандидатов → OCR-rerank по top-k (fuzzy из `migration/text/`).  
4. Если уверенность **сильно ниже** порога → «не найдено» (eval: политика slug vs null — уточнить; UI: аналоги или честный отказ).

Опциональные флаги (конфиг, не код-ветки):

- `enable_ocr_rerank`
- `enable_not_found_gate`

Пороги DINO калибруются на owner_eval / публичном сете; стартовые OCR-knobs — из `config_samples/ocr_rerank.yaml`.

Подробнее: [decision_policy.md](decision_policy.md).

## 3. Слои нового репозитория (черновик)

```
app/
  api/           # /v1/eval/predict, product search — с нуля
  core/
    cropper/     # из migration/cropper
    ocr/         # из migration/ocr
    text/        # из migration/text
    retrieve/    # DINO ONNX + pgvector — с нуля
    policy/      # margin / rerank / not_found — с нуля
  db/            # SQLAlchemy + pgvector
bin/             # yolo + dino + phocr weights
config/
docker-compose.yml   # postgres+pgvector
```

## 4. Потоки работ (независимые)

См. [streams.md](streams.md).

| ID | Фокус | Блокер |
|----|--------|--------|
| E | DINO ONNX + индекс в pgvector | схема БД |
| O | встройка fuzzy на RankedHit | нет |
| P | policy + флаги | пороги после E на owner_eval |
| V | eval endpoint + скрипт | P или заглушка slug |
| C | импорт каталога / доп. поля | Postgres up |
| U | mobile одна карточка | контракт ответа |
| I | Compose Postgres, доступ host+сеть | нет |

## 5. Postgres: compose и локальный запуск

См. [infra_postgres.md](infra_postgres.md).

Кратко: сервис `db` в Compose, порт `5432` на localhost; приложение в той же сети использует hostname `db`; локальный `uvicorn` — `localhost:5432`. Один `DATABASE_URL` через env.

## 6. Данные

- В migration: `data/owner_eval/` (прогон формата организатора).  
- Новый каталог и полевые фото — собираются отдельно, сюда не кладём.  
- Старые vine_base / set48 crop — не тащим.

## 7. Критерий готовности MVP

- Compose: Postgres up, каталог загружен, эмбеддинги в pgvector.  
- Локально: `participant_test.sh` → `predictions.jsonl` без падений.  
- UI: фото → одна карточка или not_found.  
- README: CPU vs GPU, пути к `bin/`, без секретов.
