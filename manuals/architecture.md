# Архитектура

Краткое описание компонентов, границ модулей и потоков данных. Не дублирует контракты и списки классов.

**Статус:** Stage 2 — 2A LLM OCR + 2B eval predict.

## Компоненты

| Компонент | Назначение |
|-----------|------------|
| `api` (FastAPI) | HTTP: `/health`, `/static/wines`, `POST /v1/eval/predict` |
| `api.runtime` | Старт: YOLO + DINO + DB; OCR лениво при первом rerank |
| `core.retrieve` | DINO ONNX + `WineRetriever` (crop → encode → top-K) |
| `core.policy` | Decision: margin / abs_min / OCR+fuzzy; JSONL decision log |
| `core.ocr` | `IOCREngine`: `phocr` \| `llm` \| `mock` (`create_ocr_engine`) |
| `core.text` | `FuzzyReranker` по shortlist |
| `llm` | Клиент + factory задач + адаптер LLM-OCR |
| `db` | SQLAlchemy + `WineRepository.search_by_embedding` |
| Postgres (Compose) | Каталог + `pgvector` |
| `static/wines/` | Публичные картинки каталога |
| `bin/*.onnx` | YOLO, DINO |

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
YOLO crop → DINO encode → pgvector top_k
    │
    ▼
policy.decide
    ├─ skip OCR if !enable_rerank OR margin ≥ margin_min OR single hit
    └─ else IOCREngine.recognize + FuzzyReranker on shortlist
    │
    ├── HTTP 200: {"slug": "<winner>"}   # всегда slug при непустых hits
    └── JSONL decision log (не в теле ответа)
```

Пустой каталог / 0 hits → HTTP 503.  
`score_1 < abs_min` → флаг `garbage` в логе; slug всё равно top-1.

## Границы слоёв

```
image path
  → WineRetriever.retrieve_bundle     # crop + encode + search
  → policy.decide                     # OCR только при rerank
  → emit_decision_log                 # JSONL на диск
  → {"slug": ...}                     # HTTP body без scores
```

Retriever не вызывает OCR. Policy не знает FastAPI. LLM и PHOCR — один `IOCREngine`.

## Каталог (Stage 1.2 + YOLO crop encode)

```
data/owner_database + data/site_database
  → prepare_ready_csv → wines_ready/additional
  → YOLO label crop → data/tmp/catalog_crops/{slug}.webp
       └─ fail / too small → data/tmp/catalog_crops_review/ (+ reasons.csv)
  → catalog_import:
       static/wines/{slug}.webp  = full bottle (UI / image_url)
       wines.embedding           = DINO(OK crop only); review slugs skipped
  → Postgres wines.embedding
```

Query / eval: YOLO crop → DINO; if no/empty box → **full frame** + ERROR log + `used_fallback` in decision JSONL.

**Выбор бокса YOLO (`select_label_box`):** кандидаты `score ≥ confidence`; предпочтение доли площади кадра в `[box_area_min, box_area_max]` и `conf ≥ max_conf * box_conf_keep_ratio`; среди них max `conf * (1 - dist_to_center)`; иначе max confidence.

## Внешние зависимости

- **Postgres 16 + pgvector** — `docker compose`
- **ONNX Runtime** — YOLO (CPU), DINO (cpu|cuda)
- **PHOCR** — локальный OCR (`ocr.engine=phocr`)
- **OpenAI-compatible SDK** — LLM OCR (`ocr.engine=llm`, ключ из task YAML)
