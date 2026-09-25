# Руководство по конфигурации

Зачем и когда менять настройки (профили, YAML, режимы запуска). Полные схемы ключей — в `agent_docs/contracts/`, не здесь.

**Статус:** Stage 2 — policy, ocr.engine, LLM tasks, decision log.

## Где лежат настройки

| Источник | Что задаёт |
|----------|------------|
| `.env` (копия с `.env.example`) | `DATABASE_URL`; ключи LLM (`QWEN_API_KEY` / `OPENAI_API_KEY`) — без base_url/model |
| `config/database.yaml` | `dino_model_path`, `embedding_dim`, preprocess DINO |
| `config/compute_cropper.yaml` | `compute.device` / threads, YOLO cropper, catalog crop dirs / `min_crop_side` |
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

`compute.device: cpu | cuda` в `compute_cropper.yaml` (PHOCR + DINO ORT). YOLO всегда CPU EP (отдельного флага нет).

**Локально GPU:** в конфиге `device: cuda`. Колесо `onnxruntime-gpu[cuda,cudnn]` + `LD_LIBRARY_PATH` на pip-CUDA 13 (системный CUDA 12 / `libcublasLt.so.12` **не** подходит для ORT 1.29+):

```bash
uv pip uninstall onnxruntime
uv pip install -r requirements-gpu.txt
export LD_LIBRARY_PATH="$(pwd)/.venv/lib/python3.12/site-packages/nvidia/cu13/lib:$(pwd)/.venv/lib/python3.12/site-packages/nvidia/cudnn/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
```

Без `LD_LIBRARY_PATH` CUDA EP «есть», но падает на CPU / PHOCR с `use_cuda=True` может упасть.  
`uv sync --extra ml` вернёт CPU-колесо — на локали после sync снова поставить gpu overlay.

**CPU-сервер заказчика:** `device: cpu` + `onnxruntime` из extra `ml` (не ставить `requirements-gpu.txt`).

### Каталог: YOLO crop → embedding

В `config/compute_cropper.yaml` блок `cropper`:

| Ключ | Назначение |
|------|------------|
| `min_crop_side` | Отвергнуть кроп, если ширина **или** высота меньше (по умолчанию 100) |
| `catalog_crops_dir` | Успешные кропы для DINO (`data/tmp/catalog_crops`) |
| `catalog_crops_review_dir` | Карантин: нет бокса / слишком маленький / ошибка + `reasons.csv` |
| `box_area_min` / `box_area_max` / `box_conf_keep_ratio` | Эвристика `select_label_box` (не argmax conf) |

`static/wines/` остаётся полной бутылкой для UI; в БД пишется только embedding от OK-кропа.

Import:

```bash
uv run python scripts/catalog_import.py --crop-first --recreate-wines
# или переиспользовать уже собранные кропы:
uv run python scripts/catalog_import.py --crops-dir data/tmp/catalog_crops --recreate-wines
```

### Смена размерности эмбеддинга

1. Переэкспорт DINO → `embedding_dim` в `database.yaml`.
2. Alembic на `vector(N)` + re-import.

## Чего здесь нет

- Секреты и реальные значения `.env`
- Полные схемы ключей (контракты `eval_predict.md`, `llm_engine.md`, `ocr_engine.md`)
