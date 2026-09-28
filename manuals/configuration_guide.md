# Руководство по конфигурации

Зачем и когда менять настройки (профили, YAML, режимы запуска). Полные схемы ключей — в `agent_docs/contracts/`, не здесь.

**Статус:** Stage 2 — энкодер SigLIP2, policy (confident rerank), ocr.engine, LLM tasks, decision log; Stage 3 — `product.yaml`.

## Где лежат настройки

| Источник | Что задаёт |
|----------|------------|
| `.env` (копия с `.env.example`) | `DATABASE_URL`; ключи LLM (`QWEN_API_KEY` / `OPENAI_API_KEY`) — без base_url/model |
| `config/database.yaml` | `dino_model_path` (ONNX энкодера, сейчас SigLIP2), `embedding_dim`, preprocess (`dino:`), `dino.encode_batch_size` |
| `config/compute_cropper.yaml` | `compute.device` / threads, `cropper.device`, YOLO cropper, catalog crop dirs / `min_crop_side` |
| `config/ocr_rerank.yaml` | OCR backend, fuzzy, **policy**, **decision_log** |
| `config/product.yaml` | Продукт: пороги уверенности, аналоги, хранилище запросов, отзывы, загрузка фото |
| `src/llm/tasks/*.yaml` | base_url / model / `api_key_env` / retries для LLM-задач |
| `src/llm/prompts/` | тексты промптов (путь в task YAML) |
| `docker-compose.yml` | сервис `db`, порт `5432` |
| Переменные окружения | `VINE_LOG_LEVEL` (уровень логов приложения: `DEBUG` / `INFO` / `WARNING`, по умолчанию `INFO`); `LD_LIBRARY_PATH` (GPU: библиотеки CUDA из venv, см. quickstart); `VINE_RESET_EMBEDDINGS=1` (только для смены размерности эмбеддинга) |

## Логи приложения

Uvicorn настраивает только свои логгеры (`uvicorn.*`), поэтому приложение при старте само выводит свои логи (`api.*`, `core.*`, `db.*`, `llm.*`) в stderr в формате `время уровень логгер: сообщение`. Уровень — `VINE_LOG_LEVEL` (по умолчанию `INFO`). Если логирование уже настроено хостом (pytest, внешний запускатель), приложение его не трогает. Полезные строки старта: модель и провайдеры энкодера, `OCR engine: configured=… effective=… reason=…`, `product dictionaries: …`. Решения по каждому запросу — отдельный JSONL (`decision_log`, см. ниже).

## Энкодер изображений (`config/database.yaml`)

Прод-энкодер — SigLIP2 so400m, экспорт **fp16** (`bin/siglip2_wine_p1_epoch_3_fp16.onnx`, ~817 МБ, выход `pooler_output [B, 1152]`; ссылки на скачивание — [quickstart.md](quickstart.md#5-модели--bin)). fp32-версия (`bin/siglip2_wine_p1_epoch_3.onnx`) даёт то же пространство эмбеддингов (косинус с fp16 ≥ 0.9995, ответы owner_eval совпадают 52/52) — можно подставить без переиндексации. Имена ключей (`dino_model_path`, блок `dino:`) и класс `DinoOnnxEncoder` исторические — переименование вне скоупа.

```yaml
dino_model_path: bin/siglip2_wine_p1_epoch_3_fp16.onnx
embedding_dim: 1152
dino:
  input_size: 256
  resize_mode: letterbox          # stretch = старый DINO (квадратный resize)
  pad_fill_rgb: [123, 116, 103]   # обязателен для letterbox, каналы 0..255
  normalize_mean: [0.5, 0.5, 0.5]
  normalize_std: [0.5, 0.5, 0.5]
  l2_normalize: true
  encode_batch_size: 16
```

- Препроцесс **обязан** совпадать с обучением: значения в `dino:` сверены с `siglip2_wine_p1_epoch_3_preprocess.json` (справочный файл обучения; приложение его не читает). Letterbox — одна реализация (`core/retrieve/preprocess.py`), её же использует `scripts/compare_dino_onnx.py`.
- **Fail-fast по размерности:** если статическая размерность выхода ONNX ≠ `embedding_dim`, энкодер не стартует (`RuntimeError` с путём модели и обеими размерностями). Символьные размерности не проверяются.
- **Откат на DINO:** в `database.yaml` закомментирован блок DINOv2 (768, 224, ImageNet mean/std, `resize_mode: stretch`). Раскомментировать его вместо SigLIP-блока → процедура «Смена размерности эмбеддинга» ниже.
- В decision log каждой записи пишутся `encoder_model` (имя ONNX-файла) и `embedding_dim`.

## Eval policy (`config/ocr_rerank.yaml`)

```yaml
policy:
  top_k: 5
  margin_min: 0.01
  abs_min: 0.2
  enable_rerank: true
  enable_not_found_gate: false   # Stage 3; на eval slug не влияет
  rerank_mode: confident         # always | confident
  strong_combos: [[manufacturer, grape], [manufacturer, brand]]
  max_img_drop: null             # или порог падения cosine у текстового лидера
```

OCR запускается, только если зазор `s1 - s2 < margin_min`. В режиме `confident` текстовый лидер заменяет top-1 изображения лишь при сильном подтверждении на этикетке — комбинации сигналов из `strong_combos` (производитель + сорт, производитель + бренд). В `always` текстовый лидер побеждает всегда (старое поведение). `max_img_drop` — страховка: не переключаться на кандидата, чей cosine ниже top-1 больше чем на порог.

Слова, которые **не** подтверждают производителя/бренд, задаются в `hybrid.fuzzy`: `producer_stopwords` («винодельня», «estate», «шато»…) и `generic_title_tokens` (цвет, сладость, «вино», «бленд»…).

| Когда | Что сделать |
|-------|-------------|
| A/B без OCR | `enable_rerank: false` |
| Чаще OCR | **увеличить** `margin_min` (OCR срабатывает при зазоре меньше порога) |
| Реже OCR / меньше латентность | уменьшить `margin_min` |
| Вернуть безусловный rerank | `rerank_mode: always` |
| Ложные переключения | добавить слова в `producer_stopwords` / `generic_title_tokens` или задать `max_img_drop` |
| Калибровка garbage | править `abs_min` после owner_eval |

## Продукт (`config/product.yaml`)

Читается при старте (`load_product_settings()` → `app.state.product_settings`); изменения — после рестарта. UI использует только `upload`, продуктовый сервис — всё.

```yaml
confidence:            # косинус image top-1; ПЛЕЙСХОЛДЕРЫ до калибровки
  high_min: 0.80
  medium_min: 0.65
  not_found_min: 0.50
analogs:
  limit: 5
  color_synonyms:      # слово OCR → categories.name
    Красное: [красное, красн, red, rosso, tinto, rouge]
    ...
  grape_aliases:       # сорт справочника → латинские написания (фраза целиком)
    Санджовезе: [sangiovese]
    Пино Нуар: [pinot noir, pinot nero]
    ...
storage:
  queries_dir: data/tmp/search_queries
  retention_days: 10
feedback_log: data/tmp/search_feedback.jsonl
upload:
  max_mb: 15
  content_types: [image/jpeg, image/png, image/webp]
```

| Ключ | Зачем менять |
|------|--------------|
| `confidence.high_min` / `medium_min` | Граница `found/high` → `found/medium` → `low`. Меньше — чаще «уверенный» ответ, больше ошибок среди них |
| `confidence.not_found_min` | Ниже порога — `not_found` (без победителя, только аналоги). Нужны фото вне каталога для честной калибровки |
| `analogs.limit` | Сколько аналогов в ответе поиска (у `GET /analogs` — параметр `limit`, 1..50) |
| `analogs.color_synonyms` | Ключ — точное `categories.name`; значения — слова этикетки (регистр и диакритика не важны; русские слова совпадают и с окончаниями: «красного»). Цвет без ключа просто не даёт подсказки (цвет только в `hints`, фильтром аналогов не служит) |
| `analogs.grape_aliases` | Необязательно (по умолчанию `{}`). Ключ — сорт из справочника (`GET /api/v1/dictionaries` → `grapes`); значения — латинские / OCR-написания. Совпадение — все слова фразы есть на этикетке (порядок, регистр, диакритика не важны): `SANGIOVESE` → «Санджовезе». Алиас ведёт только на свой ключ, поэтому «PINOT» отдельно не даёт «Пино Нуар». Ключ, которого нет в справочнике, игнорируется с WARNING в логе старта. Используется только продуктом (подбор аналогов неизвестного вина), на eval не влияет |
| `storage.queries_dir` | Куда сохранять фото запросов и JSON результатов (относительно корня репо) |
| `storage.retention_days` | Срок хранения; чистка при старте и `scripts/cleanup_search_queries.py` |
| `feedback_log` | JSONL отзывов «то / не то вино» |
| `upload.max_mb` / `content_types` | Лимит размера (413) и допустимые типы (415) для `POST /api/v1/search` |

**Калибровка порогов** — `scripts/calibrate_confidence.py` прогоняет `owner_eval` через `ProductService.search` и печатает распределение `score_1` для верных / неверных ответов и предложения `medium_min` / `high_min`. YAML скрипт **не меняет**; итог — `agent_docs/reports/confidence_calibration.md`, новые значения вносятся вручную после согласования.

```bash
# через работающий API
uv run python scripts/calibrate_confidence.py --endpoint http://127.0.0.1:8080/api/v1/search \
  --report agent_docs/reports/confidence_calibration.md
# без сервера (GPU занят → энкодер на CPU; OCR по цепочке: LLM при наличии ключа, иначе без OCR)
CUDA_VISIBLE_DEVICES= uv run python scripts/calibrate_confidence.py --in-process --ocr-device cpu
```

**Чистка хранилища** (cron):

```bash
uv run python scripts/cleanup_search_queries.py --dry-run      # что будет удалено
uv run python scripts/cleanup_search_queries.py --days 3        # переопределить retention_days
```

## OCR backend

```yaml
ocr:
  engine: phocr       # phocr | llm | mock
  llm_task: ocr_label
  lang: ru
  limit_side_len: 1150
```

**Цепочка выбора движка** (один раз при старте, дефолты `ocr.engine: phocr` и `compute.device` не менялись; значения `auto` нет):

| `ocr.engine` | Условие | Эффективный движок |
|---|---|---|
| `phocr` | CUDA доступна (`compute.device: cuda` и сессия энкодера реально на `CUDAExecutionProvider`) | `phocr` — как раньше |
| `phocr` | CUDA нет (`compute.device: cpu`, `CUDA_VISIBLE_DEVICES=""`, CUDA EP не загрузился) | `llm` (задача `ocr.llm_task`) |
| `phocr` / `llm` | LLM недоступен (нет / пустой ключ из task YAML, ошибка YAML / клиента) | `none` — OCR выключен, rerank пропускается, slug всё равно возвращается |
| `llm` | ключ есть | `llm` (CUDA не проверяется) |
| `mock` | — | `mock` (тесты) |

В логе старта одна строка, по ней видно итог выбора:

```
OCR engine: configured=phocr effective=phocr reason=cuda_available
OCR engine: configured=phocr effective=llm reason=no_cuda
OCR engine: configured=phocr effective=none reason=llm_unavailable: ValueError: Environment variable 'QWEN_API_KEY' is missing or empty (…)
```

Сбой LLM-OCR на конкретном запросе (исчерпаны ретраи, пустой ответ) → rerank этого запроса пропускается (`rerank_reason: ocr_failed` в decision log), аналоги неизвестного вина пустые; при `none` — `rerank_reason: ocr_unavailable`. Переключения на лету нет — повторный выбор только при рестарте. PHOCR строится **лениво** при первом rerank; при `enable_rerank: false` движок не грузится. Полноценные профили GPU / CPU — бэклог `CFG-DEVICE-001`.

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

Каждая запись содержит `score_1`, `score_2`, `margin`; записи продуктового поиска дополнительно — `search_id`, `status`, `confidence_level`, `endpoint: "product"` (у eval поля `endpoint` нет).

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

### Энкодер / device

`compute.device: cpu | cuda` в `compute_cropper.yaml` — только **PHOCR + энкодер (SigLIP2)** ORT EP.

`cropper.device: cpu | cuda | auto` (default **`cpu`**) — только **YOLO** ORT EP. Online `/v1/eval/predict` остаётся на CPU YOLO, пока YAML не переопределён. Bulk `--crop-first` может поставить `cuda` / CLI `--cropper-device`.

**VRAM:** одновременный GPU для YOLO + PHOCR + SigLIP2 может исчерпать память. Для online eval держите `cropper.device: cpu`. Для массового crop-only (без OCR) CUDA YOLO допустим.

`dino.encode_batch_size` в `config/database.yaml` (default `16`, `1` = serial) — размер ORT-батча при catalog import / re-encode. CLI: `--encode-batch-size N`.

**Локально GPU:** в конфиге `compute.device: cuda`. Колесо `onnxruntime-gpu[cuda,cudnn]` + `LD_LIBRARY_PATH` на pip-CUDA 13 (системный CUDA 12 / `libcublasLt.so.12` **не** подходит для ORT 1.29+):

```bash
uv pip uninstall onnxruntime
uv pip install -r requirements-gpu.txt
export LD_LIBRARY_PATH="$(pwd)/.venv/lib/python3.12/site-packages/nvidia/cu13/lib:$(pwd)/.venv/lib/python3.12/site-packages/nvidia/cudnn/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
```

Без `LD_LIBRARY_PATH` CUDA EP «есть», но падает на CPU / PHOCR с `use_cuda=True` может упасть.  
`uv sync --extra ml` вернёт CPU-колесо — на локали после sync снова поставить gpu overlay.

**CPU-сервер заказчика:** `compute.device: cpu` + `onnxruntime` из extra `ml` (не ставить `requirements-gpu.txt`); `cropper.device: cpu`.

### Каталог: YOLO crop → embedding

В `config/compute_cropper.yaml` блок `cropper`:

| Ключ | Назначение |
|------|------------|
| `device` | YOLO ORT: `cpu` \| `cuda` \| `auto` (default `cpu`) |
| `min_crop_side` | Отвергнуть кроп, если ширина **или** высота меньше (по умолчанию 100) |
| `catalog_crops_dir` | Успешные кропы для энкодера (`data/tmp/catalog_crops`) |
| `catalog_crops_review_dir` | Карантин: нет бокса / слишком маленький / ошибка + `reasons.csv` |
| `box_area_min` / `box_area_max` / `box_conf_keep_ratio` | Эвристика `select_label_box` (не argmax conf) |

`static/wines/` остаётся полной бутылкой для UI; в БД пишется только embedding от OK-кропа (батч энкодера через `dino.encode_batch_size`).

Import:

```bash
uv run python scripts/catalog_import.py --crop-first --recreate-wines
# GPU YOLO только на crop-pass + батч encode:
uv run python scripts/catalog_import.py --crop-first --cropper-device cuda \
  --encode-batch-size 16 --recreate-wines
# или переиспользовать уже собранные кропы:
uv run python scripts/catalog_import.py --crops-dir data/tmp/catalog_crops --recreate-wines
```

Источник каталога — CSV владельца (`data/wines_integrated_updated.csv` в git + фото `data/owner_database/images/` из облака + обогащение `data/site_database/wines_database_enriched.json` в git: рейтинг, блюда, ссылки; пустая колонка «Файл в wines_images» → `{slug}.webp`): сначала `scripts/catalog_prepare/prepare_clean_csv.py` конвертирует его в схему импорта (`wines_clean_ready.csv`, строки без фото → `wines_clean_rejected.csv` с `reason`), затем импорт с `--csv scripts/catalog_prepare/wines_clean_ready.csv`. `--csv` можно повторять; он заменяет `--ready`/`--additional`. Строки с `image_source=clean` ищут фото в `--clean-images` (по умолчанию `data/clean/images`; `rebuild_catalog_db.sh` передаёт `data/owner_database/images`).

### Смена размерности эмбеддинга

Эмбеддинги другой размерности не конвертируются — только пересчёт.

1. Новый ONNX + `embedding_dim` и `dino:` в `database.yaml` (энкодер сам проверит размерность при старте).
2. `VINE_RESET_EMBEDDINGS=1 uv run alembic upgrade head` — миграция `0002_embedding_dim` переводит `wines.embedding` в `vector(N)`. Если размерность уже совпадает — no-op. На непустой таблице без переменной миграция **отказывается** работать; с `VINE_RESET_EMBEDDINGS=1` удаляет все строки `wines`.
3. Полный реимпорт каталога (`--crop-first --recreate-wines`).

Всё вместе (подготовка CSV → миграция → импорт) делает `scripts/rebuild_catalog_db.sh --yes`; см. `quickstart.md`.

## Чего здесь нет

- Секреты и реальные значения `.env`
- Полные схемы ключей (контракты `eval_predict.md`, `llm_engine.md`, `ocr_engine.md`)
