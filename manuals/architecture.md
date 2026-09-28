# Архитектура

Краткое описание компонентов, границ модулей и потоков данных. Не дублирует контракты и списки классов.

**Статус:** Stage 2 — 2A LLM OCR + 2B eval predict; Stage 4 — веб-интерфейс поверх `ProductService`.

## Компоненты

| Компонент | Назначение |
|-----------|------------|
| `api` (FastAPI) | HTTP: `/health`, `/static/wines`, `POST /v1/eval/predict`; подключает UI-роутер и `/ui-static` |
| `core.product` | Продуктовый контракт: DTO, протокол `ProductService`, `StubProductService` |
| `web` (Jinja2) | Публичный UI: сканер, результат, каталог, «Мои вина» (`src/web/`) |
| `api.runtime` | Старт: YOLO + энкодер SigLIP2 + DB; OCR лениво при первом rerank |
| `core.retrieve` | Энкодер ONNX (SigLIP2; класс `DinoOnnxEncoder` — историческое имя) + `WineRetriever` (crop → encode → top-K) |
| `core.policy` | Decision: margin / abs_min / OCR+fuzzy (confident rerank); JSONL decision log |
| `core.ocr` | `IOCREngine`: `phocr` \| `llm` \| `mock` (`create_ocr_engine`) |
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

## Веб-интерфейс (Stage 4)

```
браузер ──HTML-формы / fetch──▶ src/web/router.py (страницы, PRG)
                                   │  views.py: view models из DTO
                                   │  templating.py: Jinja2 (autoescape, фильтры)
                                   ▼
                    request.app.state.product_service   (ProductService)
                         ├─ StubProductService   — фикстуры в памяти (сейчас)
                         └─ реальный сервис      — ветка бэкенда (YOLO → энкодер → pgvector → policy/OCR)
```

- UI получает данные **только** через `app.state.product_service`; в `src/web/` нет импортов БД, ретривера, policy и OCR, HTTP-вызовов своего `/api/v1` тоже нет. Замена заглушки на реальный сервис — одна строка в lifespan `src/api/main.py`, шаблоны не меняются.
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

## Внешние зависимости

- **Postgres 16 + pgvector** — `docker compose`
- **ONNX Runtime** — YOLO (`cropper.device`: cpu|cuda|auto), SigLIP2 (`compute.device`: cpu|cuda)
- **PHOCR** — локальный OCR (`ocr.engine=phocr`)
- **OpenAI-compatible SDK** — LLM OCR (`ocr.engine=llm`, ключ из task YAML)
