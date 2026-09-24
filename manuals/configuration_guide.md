# Руководство по конфигурации

Зачем и когда менять настройки (профили, YAML, режимы запуска). Полные схемы ключей — в `agent_docs/contracts/`, не здесь.

**Статус:** Stage 2 — policy, ocr.engine, LLM tasks, decision log.

## Где лежат настройки

| Источник | Что задаёт |
|----------|------------|
| `.env` (копия с `.env.example`) | `DATABASE_URL`; ключи LLM (`QWEN_API_KEY` / `OPENAI_API_KEY`) — без base_url/model |
| `config/database.yaml` | `dino_model_path`, `embedding_dim`, preprocess DINO |
| `config/compute_cropper.yaml` | `compute.device` / threads, YOLO cropper |
| `config/ocr_rerank.yaml` | OCR backend, fuzzy, **policy**, **decision_log** |
| `src/llm/tasks/*.yaml` | base_url / model / `api_key_env` / retries для LLM-задач |
| `src/llm/prompts/` | тексты промптов (путь в task YAML) |
| `docker-compose.yml` | сервис `db`, порт `5432` |

## Eval policy (`config/ocr_rerank.yaml`)

```yaml
policy:
  top_k: 5
  margin_min: 0.1
  abs_min: 0.2
  enable_rerank: true
  enable_not_found_gate: false   # Stage 3; на eval slug не влияет
```

| Когда | Что сделать |
|-------|-------------|
| A/B без OCR | `enable_rerank: false` |
| Чаще OCR | уменьшить `margin_min` |
| Калибровка garbage | править `abs_min` после owner_eval |

## OCR backend

```yaml
ocr:
  engine: phocr       # phocr | llm | mock
  llm_task: ocr_label
  lang: ru
  limit_side_len: 1150
```

OCR поднимается **лениво** при первом rerank. При `enable_rerank: false` движок не грузится.

## LLM tasks (Stage 2A)

Задача `ocr_label` — `src/llm/tasks/ocr_label.yaml`:

- Provider inline (по умолчанию Qwen DashScope-compatible).
- `api_key_env: QWEN_API_KEY` — только имя переменной; значение в `.env`.
- `retries: 3` — connect/timeout, HTTP 408/429/5xx; другие 4xx без retry.
- Промпт: `src/llm/prompts/ocr_label_v1.md` (только видимый текст этикетки).

Смена модели/URL — правка task YAML, не `.env`. Другой провайдер — другой `api_key_env` + ключ в `.env.example`.

## Decision log

```yaml
decision_log:
  path: data/tmp/eval_decisions.jsonl
  ocr_lines_cap: 32
```

```bash
uv run python scripts/collect_eval_report.py \
  --log data/tmp/eval_decisions.jsonl \
  --predictions data/owner_eval/1/predictions.jsonl \
  --mapping data/owner_eval/1/mapping.json
```

## Типовые сценарии

### Локальная БД

1. `docker compose up -d`
2. `.env` с `DATABASE_URL=postgresql+psycopg://vine:vine@127.0.0.1:5432/vine`
3. `uv run alembic upgrade head`

### DINO / device

`compute.device: cpu | cuda` в `compute_cropper.yaml`. YOLO всегда CPU EP.

### Смена размерности эмбеддинга

1. Переэкспорт DINO → `embedding_dim` в `database.yaml`.
2. Alembic на `vector(N)` + re-import.

## Чего здесь нет

- Секреты и реальные значения `.env`
- Полные схемы ключей (контракты `eval_predict.md`, `llm_engine.md`, `ocr_engine.md`)
