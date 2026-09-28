# Архитектура

Краткое описание компонентов, границ модулей и потоков данных. Не дублирует контракты и списки классов.

**Статус:** Stage 2 — 2A LLM OCR + 2B eval predict; Stage 3 — продуктовый API `/api/v1/*` (`CatalogProductService`); Stage 4 — веб-интерфейс поверх того же `ProductService`.

## Компоненты

| Компонент | Назначение |
|-----------|------------|
| `api` (FastAPI) | HTTP: `/health`, `/static/wines`, `POST /v1/eval/predict`, `/api/v1/*` (продукт); подключает UI-роутер и `/ui-static` |
| `api.runtime` | Старт: YOLO + энкодер SigLIP2 + DB; один раз выбирает OCR-движок (цепочка CUDA → PHOCR, иначе LLM, иначе без OCR); PHOCR прогревается в `lifespan` до приёма запросов (первый старт качает веса), при сбое прогрева — лениво при первом rerank |
| `api.eval_pipeline` | Общий пайплайн `run_search` (retrieve → decide → decision log) для eval и продукта |
| `core.product` | DTO + `ProductService`; `CatalogProductService` (поиск, аналоги, каталог, справочники, отзывы); `StubProductService` — для тестов UI |
| `web` (Jinja2) | Публичный UI: сканер, результат, каталог, «Мои вина» (`src/web/`); вызывает тот же `ProductService` in-process |
| `core.retrieve` | Энкодер ONNX (SigLIP2; класс `DinoOnnxEncoder` — историческое имя) + `WineRetriever` (crop → encode → top-K) |
| `core.policy` | Decision: margin / abs_min / OCR+fuzzy (confident rerank); JSONL decision log |
| `core.ocr` | `IOCREngine`: `phocr` \| `llm` \| `mock` (`create_ocr_engine`); `select_ocr_engine` — чистая функция выбора движка; `OCRUnavailableError` — сбой LLM-OCR на запросе |
| `core.text` | `FuzzyReranker` по shortlist |
| `llm` | Клиент + factory задач + адаптер LLM-OCR |
| `db` | SQLAlchemy + `WineRepository.search_by_embedding` |
| Postgres (Compose) | Каталог + `pgvector` |
| `static/wines/` | Публичные картинки каталога |
| `bin/*.onnx` | YOLO, SigLIP2 (+ `*_preprocess.json`); DINOv2 — только для отката |

## LLM-слой (Stage 2A)

```
create_ocr_engine("llm", llm_task="ocr_label")
        │
        ▼
LLMOCREngine  →  create_llm_engine("ocr_label")
                      │
                      ├─ src/llm/tasks/ocr_label.yaml  (base_url, model, api_key_env, retries)
                      ├─ src/llm/prompts/ocr_label_v1.md
                      └─ OpenAI-compatible client (retry 408/429/5xx; default retries=3)
```

- Вызывающий передаёт только **имя задачи**; URL/model не в `.env`.
- Выход `text_lines` → `list[str]` — тот же контракт, что у PHOCR.
- Реестра провайдеров нет: provider inline в task YAML.

## Eval pipeline (Stage 2B)

```
multipart image
    │
    ▼
temp upload (data/tmp/uploads) ── cleanup after request
    │
    ▼
YOLO crop → SigLIP2 encode (letterbox 256, L2) → pgvector top_k
    │
    ▼
policy.decide
    ├─ skip OCR if !enable_rerank OR margin ≥ margin_min OR single hit
    ├─ нет OCR-движка (effective=none)      → skip, rerank_reason=ocr_unavailable
    ├─ LLM-OCR упал (OCRUnavailableError)   → skip, rerank_reason=ocr_failed
    └─ else IOCREngine.recognize + FuzzyReranker on shortlist
         ├─ rerank_mode=always    → текстовый лидер = winner
         └─ rerank_mode=confident → label_evidence (производитель / сорт / бренд)
              ├─ лидер = top-1 изображения          → top-1 (text_agrees)
              ├─ сильная комбинация (strong_combos),
              │  токен отличает лидера от top-1     → лидер (strong_text)
              └─ слабо / не отличает / конфликт /
                 падение cosine > max_img_drop      → top-1 (weak_text, not_distinguishing,
                                                            text_conflict, img_drop)
    │
    ├── HTTP 200: {"slug": "<winner>"}   # всегда slug при непустых hits
    └── JSONL decision log (не в теле ответа)
```

### Выбор OCR-движка (цепочка)

Выполняется один раз при старте (`build_eval_runtime` → `core.ocr.selection.select_ocr_engine`), в лог пишется одна строка `OCR engine: configured=… effective=… reason=…`:

| `ocr.engine` | Условие | Эффективный движок | `reason` |
|---|---|---|---|
| `phocr` | CUDA доступна | `phocr` (как раньше, `use_cuda=True`, прогрев при старте) | `cuda_available` |
| `phocr` | CUDA нет | `llm` (задача `ocr.llm_task`) | `no_cuda` |
| `phocr` / `llm` | LLM недоступен (нет ключа, ошибка YAML / клиента) | `none` | `llm_unavailable: <класс ошибки: сообщение>` |
| `llm` | LLM доступен | `llm` (без проверки CUDA) | `configured_llm` |
| `mock` | — | `mock` | `configured_mock` |

«CUDA доступна» = `compute.device: cuda` **и** уже созданная сессия энкодера SigLIP2 реально работает на `CUDAExecutionProvider` (`session.get_providers()`); список `ort.get_available_providers()` не показателен (он содержит CUDA и при `CUDA_VISIBLE_DEVICES=""`). При `none` rerank пропускается, eval всё равно отдаёт slug (top-1 изображения). Переключения движка на лету нет — повторный выбор только при рестарте.

Пустой каталог / 0 hits → HTTP 503.  
`score_1 < abs_min` → флаг `garbage` в логе; slug всё равно top-1.  
В decision log: `rerank_reason`, `text_leader`, `evidence`, а также `encoder_model` / `embedding_dim` для трассировки версии энкодера.

## Границы слоёв

```
image path
  → WineRetriever.retrieve_bundle     # crop + encode + search
  → policy.decide                     # OCR только при rerank
  → emit_decision_log                 # JSONL на диск
  → {"slug": ...}                     # HTTP body без scores
```

Retriever не вызывает OCR. Policy не знает FastAPI. LLM и PHOCR — один `IOCREngine`.

Общий код — `api.eval_pipeline.run_search(runtime, path, log_fields=...)` → `SearchRun(bundle, decision, latency_ms)`. `predict_slug` (eval) и `CatalogProductService.search` (продукт) вызывают одну функцию, поэтому ответ eval не меняется. Вызовы моделей (ONNX / OCR) сериализованы общим локом: продуктовые роуты работают в threadpool.

## Продуктовый поток (Stage 3)

Контракт — `agent_docs/contracts/product_api.md`. JSON API (`src/api/routers/product.py`) и Jinja UI вызывают **один** in-process `ProductService` (`app.state.product_service`), UI не ходит в `/api/v1` по HTTP.

```
POST /api/v1/search (multipart image)
    │  проверка: content-type ∈ upload.content_types, размер ≤ upload.max_mb
    │  (потоково, во временный файл data/tmp/uploads), Pillow-декодирование
    ▼
CatalogProductService.search
    ├─ копия фото → {queries_dir}/{search_id}{ext}      # search_id = uuid4 hex
    ├─ run_search (тот же пайплайн, что eval) → decision
    ├─ score_1 → status / confidence_level (пороги product.yaml → confidence)
    │     score_1 < not_found_min  → not_found / low, winner = None
    │     ≥ high_min → found/high;  ≥ medium_min → found/medium;  иначе low/low
    ├─ low / not_found → аналоги по сорту из OCR
    ├─ decision log + search_id, status, confidence_level, endpoint="product"
    └─ SearchResult → {queries_dir}/{search_id}.json
```

### Аналоги

Правило: **один фильтр — один сорт**, без цепочки повторов (решение владельца 2026-09-28).

| Случай | `source` | Фильтры | OCR |
|---|---|---|---|
| Известное вино: `found`, запрос `GET /search/{id}/analogs` | `winner_filters` | первый сорт победителя из БД; `exclude_manufacturer` = производитель победителя; `exclude_slugs=[winner]`; цвет не задаётся | не вызывается |
| Неизвестное вино: `low` / `not_found` (считается в `search`, `analogs_for` берёт сохранённые подсказки) | `ocr_filters` | только первый сорт из OCR; `exclude_slugs=[winner]`, если есть (low) победитель; цвет / производитель не задаются | единственный источник сорта |

Нет сорта (у победителя в БД / в OCR, OCR отключён или упал) → пустой результат **без запроса в БД** (`wines=[]`, `total=0`). Сорт есть, но 0 совпадений → пусто, без повтора. Пустой результат сохраняет свой `source`; UI показывает «Аналог подобрать не удалось». Выдача — до `limit` вин по `public_rating DESC NULLS LAST`, `id`; `total` — полное число совпадений. `vector` в `AnalogSource` зарезервирован и сервисом не выдаётся.

`hints` (для показа, фильтром не применяются): известное вино — цвет и сорт победителя (`ocr_ran=False`); неизвестное — полные OCR-подсказки.

OCR-подсказки (`core/product/hints.py`, чистые функции без БД/OCR): строки OCR берутся из `decision.ocr_lines`, если rerank уже был, иначе OCR запускается на кропе выбранным при старте движком. Если policy пропустила rerank из-за OCR (`rerank_reason` = `ocr_unavailable` / `ocr_failed`) или движка нет / он упал — `OcrHints(ocr_ran=False)`, поиск не падает. Сорт — целое название из справочника: все токены на этикетке (как `label_evidence`: кириллица, транслит, общие алиасы `normalize.py`) **или** целая латинская фраза из `analogs.grape_aliases` (`SANGIOVESE` → «Санджовезе», `PINOT NOIR` → «Пино Нуар»); «ПИНО» отдельно не даёт «Пино Гри». Несколько сортов — сначала более длинные названия, затем порядок справочника. Цвет — словарь `analogs.color_synonyms`; производитель — compact-совпадение с каталогом через `FuzzyReranker` (оба — только в `hints`).

### Справочники

Строятся **один раз** при создании сервиса (обновление = рестарт): цвета / регионы / сладость — значения `categories` / `regions` / `sweetness_levels`, которые есть хотя бы у одного вина; сорта — `wines.grape_variety`, разбитые по `,;/+` («н/д» отбрасывается); блюда — `unnest(wines.dishes)`. Дедупликация без учёта регистра, ё/е и пунктуации, сортировка без учёта регистра (`core/product/vocabulary.py`). Фильтр по значению справочника раскрывается во все исходные написания из БД.

### Хранилище запросов и отзывы

- `storage.queries_dir` (по умолчанию `data/tmp/search_queries/`, в `.gitignore`): `{id}{ext}` + `{id}.json`. Фото отдаётся только по точному id (`^[0-9a-f]{32}$`, capability URL), каталог не листается; путь проверяется на выход за пределы директории.
- Файлы старше `storage.retention_days` удаляются при старте сервиса и скриптом `scripts/cleanup_search_queries.py` (cron, `--dry-run`, `--days`). Трогаются только файлы вида `{id}.*`.
- Отзывы «то / не то вино» — строка JSONL в `feedback_log` (`data/tmp/search_feedback.jsonl`), не в БД и не в decision log: `ts, search_id, slug, verdict, status, confidence_level, winner_slug`.

### Каталог

`find_wines` / `get_wine` → `WineRepository.search_filters` + `count_filters` (одни и те же фильтры): `color` → `categories.name`, `grape` → целый элемент `grape_variety` (regex по разделителям `,;/+`, без учёта регистра), `dish` → пересечение с `dishes`, `exclude_manufacturer`, `exclude_slugs`. Каждый вызов сервиса — своя сессия (`session_scope`).

## Веб-интерфейс (Stage 4)

```
браузер ──HTML-формы / fetch──▶ src/web/router.py (страницы, PRG)
                                   │  views.py: view models из DTO
                                   │  templating.py: Jinja2 (autoescape, фильтры)
                                   ▼
                    request.app.state.product_service   (ProductService)
                         ├─ CatalogProductService — рабочий сервис (YOLO → энкодер → pgvector → policy/OCR)
                         └─ StubProductService    — фикстуры в памяти (только тесты UI)
```

- UI получает данные **только** через `app.state.product_service`; в `src/web/` нет импортов БД, ретривера, policy и OCR, HTTP-вызовов своего `/api/v1` тоже нет. В lifespan `src/api/main.py` подключён `CatalogProductService`; UI и `/api/v1` работают с одним экземпляром.
- Лимиты загрузки (размер, типы) — из `app.state.product_settings.upload` (`config/product.yaml`), те же, что у API. Тип файла определяется по сигнатуре содержимого, а не по имени. Временный файл — `data/tmp/uploads/`, удаляется сразу после `service.search`.
- Поток поиска: `POST /search` → 303 на `/result/{search_id}` (Post/Redirect/Get). Отзыв «Это то вино?» — `POST /result/{id}/feedback` → 303 на результат с `?fb=1`. Аналоги для «найдено» — по кнопке (`?analogs=1` → `service.analogs_for`).
- Уверенность показывается только текстом (высокая / средняя / низкая), без процентов и cosine; `candidates` в UI не выводятся.
- Прогрессивное улучшение: все сценарии работают обычными формами без JS. Модули `static/js/`: `camera.js` (камера, полный кадр в JPEG; «прицел» — только визуальный), `upload.js` (drag&drop, ошибки без перезагрузки), `lightbox.js` (просмотр фото с зумом), `store.js` («Мои вина» в `localStorage`, ключи `svoe_vino:v1:*`), `ui.js` (панель фильтров, заглушки «Скоро», запасная картинка).
- «Личный кабинет» — без сервера: история поисков (без фото), избранное, мои оценки и отметки хранятся в браузере; вход — демо-кнопка без логина.
- Адаптивность одними шаблонами (CSS media queries): телефон < 768px — нижняя таб-панель и липкая панель действий; 768–1023px — та же раскладка с сеткой в 2 колонки; ≥ 1024px — меню в шапке, две колонки, фильтры каталога сбоку.

## Каталог (Stage 1.2 + YOLO crop encode)

```
data/owner_database + data/site_database → prepare_ready_csv → wines_ready/additional
  или
data/owner_database (wines_integrated_updated.csv + images) → prepare_clean_csv → wines_clean_ready
  → YOLO label crop → data/tmp/catalog_crops/{slug}.webp
       └─ fail / too small → data/tmp/catalog_crops_review/ (+ reasons.csv)
  → catalog_import:
       static/wines/{slug}.webp  = full bottle (UI / image_url)
       wines.embedding           = SigLIP2(OK crop, batched via dino.encode_batch_size);
                                   review slugs (no crop) → full bottle (rebuild_catalog_db.sh)
  → Postgres wines.embedding vector(embedding_dim)
```

Размерность колонки задаёт `database.yaml`; миграция `0002_embedding_dim` приводит `vector(N)` к конфигу (непустую таблицу — только с `VINE_RESET_EMBEDDINGS=1`), после чего нужен полный реимпорт.

Query / eval: YOLO crop → SigLIP2; if no/empty box → **full frame** + ERROR log + `used_fallback` in decision JSONL.

**Выбор бокса YOLO (`select_label_box`):** кандидаты `score ≥ confidence`; предпочтение доли площади кадра в `[box_area_min, box_area_max]` и `conf ≥ max_conf * box_conf_keep_ratio`; среди них max `conf * (1 - dist_to_center)`; иначе max confidence.

**Device:** YOLO EP — `cropper.device` (`cpu` \| `cuda` \| `auto`, default `cpu`). PHOCR + SigLIP2 — `compute.device`. Online eval оставляет YOLO на CPU, чтобы не делить VRAM с OCR/энкодером.

## Развёртывание

| Режим | Файл | Что в Docker |
|---|---|---|
| Основной (GPU, Linux / Windows + WSL2) | `docker-compose.full.yml` + `Dockerfile` | `db` (pgvector) и `app` (FastAPI + UI, GPU через NVIDIA Container Toolkit); миграции при старте `app`, индексация — `docker compose run --rm app scripts/rebuild_catalog_db.sh --yes` |
| Разработка / CPU | `docker-compose.yml` | только `db`; приложение на хосте через `uv` |

В образ входят код и конфиги; модели (`bin/`, только чтение), данные (`data/`) и фото каталога (`static/wines/`) подключаются томами из репозитория, веса PHOCR — именованный том `phocr_models`. Библиотеки CUDA 13 / cuDNN 9 — pip-колёса `onnxruntime-gpu[cuda,cudnn]` внутри образа (CUDA Toolkit на хосте не нужен). Проекты compose разные (`vine` и `lct_vine_final`) — у каждого своя БД.

## Внешние зависимости

- **Postgres 16 + pgvector** — `docker compose`
- **ONNX Runtime** — YOLO (`cropper.device`: cpu|cuda|auto), SigLIP2 (`compute.device`: cpu|cuda)
- **PHOCR** — локальный OCR (`ocr.engine=phocr`)
- **OpenAI-compatible SDK** — LLM OCR (`ocr.engine=llm`, ключ из task YAML)
