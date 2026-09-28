# Быстрый запуск

Полная инструкция: от чистой машины до открытой страницы сканера. Детали модулей — [architecture.md](architecture.md), настройки — [configuration_guide.md](configuration_guide.md), описание экранов — [user_interface.md](user_interface.md).

**Схема запуска.** В Docker работает только PostgreSQL + pgvector (`docker-compose.yml`). Приложение (FastAPI: eval API, продуктовый API и веб-интерфейс в одном процессе) запускается на хосте через `uv`. GPU использует приложение на хосте, а не контейнер.

## 0. Требования

| Что | Зачем | Проверка |
|---|---|---|
| Linux x86_64 (проверено на Ubuntu 22.04 / 24.04) | — | `uname -m` → `x86_64` |
| Docker Engine + Docker Compose v2 | PostgreSQL + pgvector | `docker --version`, `docker compose version` |
| `git`, `curl` | клон репозитория, установщики | — |
| `uv` | Python 3.12 и зависимости | `uv --version` |
| ~15 ГБ диска | venv (с GPU-колёсами ~4 ГБ), модели ~0.9 ГБ, фото каталога ~0.15 ГБ, БД | `df -h .` |
| Интернет при первой установке | пакеты PyPI, веса PHOCR (~270 МБ, скачиваются при первом OCR) | — |
| **Опционально:** NVIDIA GPU + драйвер ≥ 580 (CUDA 13) | ускорение энкодера (~40 мс против ~1 с на CPU) и OCR | `nvidia-smi` → `CUDA Version: 13.x` |

## 1. Docker и Docker Compose

Если уже установлены — пропустите. Официальная инструкция: [Install Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/) (Compose v2 ставится пакетом `docker-compose-plugin`).

```bash
# Ubuntu: официальный репозиторий Docker
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# запуск docker без sudo (перелогиниться после команды)
sudo usermod -aG docker "$USER"

docker run --rm hello-world
docker compose version
```

## 2. Драйвер NVIDIA (только для GPU)

Нужен **только драйвер** на хосте. CUDA Toolkit и cuDNN ставить не нужно — нужные библиотеки CUDA 13 / cuDNN 9 приходят pip-колёсами (шаг 4). **NVIDIA Container Toolkit не нужен**: в Docker крутится только Postgres, GPU ему не нужен.

```bash
# Ubuntu: рекомендуемый драйвер (или явно: sudo apt install nvidia-driver-580)
sudo ubuntu-drivers install
sudo reboot

nvidia-smi        # должно показать GPU и "CUDA Version: 13.0" или выше
```

Без GPU всё работает на CPU (медленнее, см. шаг 4 «Вариант CPU»).

## 3. uv и репозиторий

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh     # установщик uv (https://docs.astral.sh/uv/)
exec $SHELL -l                                        # подхватить PATH

git clone <URL репозитория> lct_vine_final
cd lct_vine_final
```

Все дальнейшие команды — из корня репозитория.

## 4. Python-окружение

```bash
uv python install 3.12
uv sync --python 3.12 --extra ml --extra db --extra dev
```

Это базовый (CPU) набор: колесо `onnxruntime`, OpenCV, PHOCR, SQLAlchemy/pgvector, pytest.

### Вариант GPU (рекомендуется, если есть NVIDIA)

Колёса `onnxruntime` (CPU) и `onnxruntime-gpu` в одном окружении не уживаются — ставим GPU-overlay поверх:

```bash
uv pip uninstall onnxruntime
uv pip install -r requirements-gpu.txt       # onnxruntime-gpu[cuda,cudnn] + pip-колёса CUDA 13 / cuDNN 9

# библиотеки CUDA из venv — нужно в КАЖДОМ терминале перед запуском приложения / индексации
export LD_LIBRARY_PATH="$(pwd)/.venv/lib/python3.12/site-packages/nvidia/cu13/lib:$(pwd)/.venv/lib/python3.12/site-packages/nvidia/cudnn/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

uv run python -c "import onnxruntime as o; print(o.get_available_providers())"
# ожидается: [..., 'CUDAExecutionProvider', 'CPUExecutionProvider']
```

`config/compute_cropper.yaml` → `compute.device: cuda` (значение по умолчанию в репозитории).

> После GPU-overlay **не запускайте `uv sync`** — он вернёт CPU-колесо `onnxruntime`. Обычный `uv run …` безопасен. Если всё же вернулось — повторите две команды `uv pip …` выше.

### Вариант CPU

Ничего дополнительно ставить не нужно. В `config/compute_cropper.yaml` поставьте `compute.device: cpu`. OCR без CUDA автоматически переключается на LLM (нужен ключ `QWEN_API_KEY` в `.env`), без ключа — работает без OCR (поиск только по изображению). Итог выбора виден в логе старта (шаг 9).

## 5. Модели → `bin/`

Модели не хранятся в git. Скачайте (в браузере, кнопка «Скачать») и положите **с этими именами**:

| Файл в `bin/` | Назначение | Ссылка | Запасная ссылка |
|---|---|---|---|
| `bin/yolo_detect_labels_2.onnx` (~12 МБ) | YOLO — детектор этикетки (кроп) | [Google Drive](https://drive.google.com/file/d/1uKGYwkL7Ycm5QMgsWDl5KrTOpwwtCrtg/view?usp=drive_link) | [Google Drive (alt)](https://drive.google.com/file/d/1fZhse4rYECP1jjcPX2TwDg7lTK2l9dTU/view?usp=drive_link) |
| `bin/siglip2_wine_p1_epoch_3_fp16.onnx` (~817 МБ) | SigLIP2 so400m (дообучен на вине), fp16 — энкодер изображений, вектор 1152 | [Google Drive](https://drive.google.com/file/d/1zVKvqYtkcNy-_OF8mIKMl_RVp-HHhOqK/view?usp=drive_link) | [Google Drive (alt)](https://drive.google.com/file/d/1wSSgStfcpW-JXLJvtdpUQAcWGXMQ8RoH/view?usp=drive_link) |

Из консоли (опционально, утилита `gdown` запускается через `uvx`, в проект не ставится):

```bash
mkdir -p bin
uvx gdown --fuzzy 'https://drive.google.com/file/d/1uKGYwkL7Ycm5QMgsWDl5KrTOpwwtCrtg/view' -O bin/yolo_detect_labels_2.onnx
uvx gdown --fuzzy 'https://drive.google.com/file/d/1zVKvqYtkcNy-_OF8mIKMl_RVp-HHhOqK/view' -O bin/siglip2_wine_p1_epoch_3_fp16.onnx
ls -la bin/
```

Пути прописаны в конфиге: `config/compute_cropper.yaml` → `yolo_model_path: bin/yolo_detect_labels_2.onnx`, `config/database.yaml` → `dino_model_path: bin/siglip2_wine_p1_epoch_3_fp16.onnx`, `embedding_dim: 1152`. При несовпадении размерности приложение и импорт падают при старте с понятной ошибкой.

**PHOCR** (локальный OCR этикеток) качает свои веса (~270 МБ, modelscope.cn) сам при первом запросе, где нужен OCR, — в папку пакета внутри `.venv`. Нужен интернет один раз.

## 6. Файл `.env`

```bash
cp .env.example .env
```

- `DATABASE_URL=postgresql+psycopg://vine:vine@127.0.0.1:5432/vine` — уже совпадает с `docker-compose.yml`.
- `QWEN_API_KEY` — нужен только для OCR через LLM (режим без CUDA). Не коммитьте `.env`.

## 7. База данных (PostgreSQL + pgvector)

```bash
docker compose up -d
docker compose ps                  # STATUS: healthy (≈10 с)
uv run alembic upgrade head        # схема: таблицы каталога + колонка vector(1152)
```

Данные БД живут в Docker-томе `pgdata` и переживают `docker compose down`/перезагрузку. Полный сброс тома — `docker compose down -v` (**удаляет каталог**, потом снова шаги 7–8).

## 8. Каталог и индексация

### Исходные данные

| Что | Где | В git |
|---|---|---|
| Список вин, по которому собрана БД (владелец, 2103 вина) | `data/wines_integrated_updated.csv` | да |
| Обогащение с сайта: рейтинг, блюда, ссылка на страницу, крепость, температура подачи | `data/site_database/wines_database_enriched.json` | да |
| Список проблемных фото | `data/wines_problem_images.csv` | да |
| Фото бутылок `{slug}.webp` (2091 файл, ~130 МБ) | `data/owner_database/images/` | нет — скачать |

Фото каталога — папка в облаке: [images (Google Drive)](https://drive.google.com/drive/folders/1HYiy0he8OdAui_56cIZ8xUhYXN-mJo81?usp=drive_link). В браузере: папка → «Скачать» (Google Drive отдаёт один или несколько zip). Распакуйте так, чтобы файлы лежали прямо в `data/owner_database/images/`:

```bash
mkdir -p data/owner_database/images /tmp/vine_images
for z in ~/Downloads/images-*.zip; do unzip -o "$z" -d /tmp/vine_images; done
find /tmp/vine_images -name '*.webp' -exec mv -t data/owner_database/images/ {} +
ls data/owner_database/images | wc -l        # 2091
```

(`gdown --folder` для этой папки не подходит — он скачивает не больше 50 файлов.)

**Про фото.** Часть совсем мелких фото (меньше 200 px) заменена на более крупные. Список проблемных позиций приложен — `data/wines_problem_images.csv` (100 строк): 88 — мелкие фото (из них 7 ещё и дубли чужого фото), 12 — вина без фото (нет ни фото, ни страницы на сайте). Эти 12 в индекс не попадают: 2103 вина в CSV − 12 = 2091 в БД.

### Индексация (одна команда)

```bash
# GPU: в этом терминале должен быть экспортирован LD_LIBRARY_PATH (шаг 4)
docker compose up -d
scripts/rebuild_catalog_db.sh --yes
```

Что делает скрипт (`--yes` обязателен — таблица `wines` очищается и заливается заново):

1. **CSV** — `data/wines_integrated_updated.csv` + JSON сайта → `scripts/catalog_prepare/wines_clean_ready.csv` (отбракованные — `wines_clean_rejected.csv`).
2. **Ассеты** — YOLO вырезает этикетку из каждого фото → `data/tmp/catalog_crops/` (это кодируется в БД); полные бутылки → `static/wines/` (их показывает UI). Сверка: `data/tmp/catalog_assets_check.csv`. Старые ассеты уезжают в `.trash/`.
3. **БД** — `alembic upgrade head` (с `VINE_RESET_EMBEDDINGS=1`), кодирование кропов SigLIP2 и вставка в `wines`; фото, где YOLO не нашёл этикетку, кодируются целиком.

Время: на GPU — минуты, на CPU — заметно дольше (кодирование ~1 с на фото). Батч энкодера — `-- --encode-batch-size 8` (уменьшить при нехватке видеопамяти).

Раздельно: `scripts/rebuild_catalog_db.sh --prepare-only` (шаги 1–2, БД не трогается), затем `scripts/rebuild_catalog_db.sh --yes --reuse-assets` (шаг 3).

### Проверка

```bash
docker compose exec -T db psql -U vine -d vine -c "SELECT count(*), count(embedding) FROM wines;"
# ожидается: 2091 | 2091
ls static/wines | wc -l                                  # 2091
```

## 9. Запуск решения

```bash
# GPU: export LD_LIBRARY_PATH=... (шаг 4) в этом терминале
uv run uvicorn api.main:app --app-dir src --host 0.0.0.0 --port 8080
```

Старт занимает ~10 с. В логе должны быть строки:

```text
INFO core.retrieve.dino_encoder: Encoder ONNX model=siglip2_wine_p1_epoch_3_fp16.onnx providers=['CUDAExecutionProvider', ...] embedding_dim=1152 ...
INFO api.runtime: OCR engine: configured=phocr effective=phocr reason=cuda_available
INFO core.product.catalog_service: product dictionaries: 4 colors, 139 grapes, ...
INFO:     Uvicorn running on http://0.0.0.0:8080
```

На CPU вместо `CUDAExecutionProvider` будет только `CPUExecutionProvider`, а OCR — `effective=llm` или `effective=none` с причиной. Подробность логов — переменная `VINE_LOG_LEVEL` (`DEBUG` / `INFO` / `WARNING`, по умолчанию `INFO`).

### Открыть

| Адрес | Что |
|---|---|
| [http://127.0.0.1:8080/](http://127.0.0.1:8080/) | **Веб-интерфейс** — сканер этикетки (описание экранов — [user_interface.md](user_interface.md)) |
| [http://127.0.0.1:8080/catalog](http://127.0.0.1:8080/catalog) | Каталог с фильтрами |
| [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs) | Swagger: все JSON-эндпоинты |
| [http://127.0.0.1:8080/health](http://127.0.0.1:8080/health) | `{"status":"ok"}` |

С другого устройства в сети — `http://<IP-компьютера>:8080/`. **Камера на телефоне требует HTTPS** (браузер даёт доступ к камере только в защищённом контексте или на `localhost`); по обычному `http://<IP>` работает загрузка фото из галереи. Для демо камеры — HTTPS-туннель или сертификат перед uvicorn.

### Smoke-проверка из консоли

```bash
curl -s http://127.0.0.1:8080/health
curl -s -F "image=@./data/owner_eval/1/queries/04f3ce15.jpg" http://127.0.0.1:8080/v1/eval/predict
# {"slug":"chateau-de-talu-ruzh-kaberne-sovinon-krasnoe-suhoe-14"}
```

(`data/owner_eval/` — набор организатора; если его нет, подставьте любое фото этикетки.)

### Остановка

`Ctrl+C` в терминале uvicorn; БД — `docker compose down` (данные сохраняются в томе).

## 10. Продуктовый API (`/api/v1`)

Тот же процесс. Пороги и лимиты — `config/product.yaml` ([configuration_guide.md](configuration_guide.md)).

| Метод / путь | Ответ |
|---|---|
| `POST /api/v1/search` (multipart **`image`**) | `SearchResult`: `search_id`, `status` (`found` / `low` / `not_found`), `confidence_level`, `winner`, `candidates` (top-5), `analogs` |
| `GET /api/v1/search/{search_id}` | сохранённый `SearchResult` |
| `GET /api/v1/search/{search_id}/analogs?limit=5` | `AnalogsResult`: `winner_filters` (найденное вино — тот же сорт, другие производители) / `ocr_filters` (неизвестное вино — сорт с этикетки); пустой `wines` = «аналог подобрать не удалось» |
| `GET /api/v1/wines/{slug}` | `WineCard` |
| `GET /api/v1/wines?color=&grape=&region=&sweetness=&dish=&exclude_manufacturer=&limit=5&offset=0` | `{"items": [...], "total": N}` |
| `GET /api/v1/dictionaries` | цвета, сорта, регионы, сладость, блюда |
| `POST /api/v1/feedback` (JSON) | 204 |

Ошибки — `{"detail": "..."}`: 400 пустой / недекодируемый файл, 413 больше `upload.max_mb`, 415 тип не из `upload.content_types`, 422 неверные параметры, 404 нет поиска / вина, 503 пустой каталог.

```bash
B=http://127.0.0.1:8080/api/v1
curl -s -F "image=@./data/owner_eval/1/queries/26ddb066.jpg" $B/search | tee /tmp/search.json
SID=$(python3 -c "import json; print(json.load(open('/tmp/search.json'))['search_id'])")
curl -s $B/search/$SID
curl -s "$B/search/$SID/analogs?limit=5"
curl -s -G $B/wines --data-urlencode color=Красное --data-urlencode grape=Саперави --data-urlencode limit=3
curl -s $B/wines/agora-muskat-chernyj
curl -s $B/dictionaries
curl -s -o /dev/null -w "%{http_code}\n" -H 'Content-Type: application/json' \
  -d "{\"search_id\":\"$SID\",\"verdict\":\"match\"}" $B/feedback      # 204
```

Фото запросов и JSON результатов — `data/tmp/search_queries/` (хранятся 10 дней), отзывы — `data/tmp/search_feedback.jsonl`, лог решений — `data/tmp/eval_decisions.jsonl`. Чистка по сроку — при старте и `uv run python scripts/cleanup_search_queries.py [--dry-run] [--days N]`.

## 11. Eval организатора (owner_eval)

Приложение должно слушать `:8080`:

```bash
./data/owner_eval/1/participant_test.sh \
  --images-dir ./data/owner_eval/1/queries \
  --manifest ./data/owner_eval/1/queries.tsv \
  --endpoint 'http://127.0.0.1:8080/v1/eval/predict' \
  --output ./data/owner_eval/1/predictions.jsonl
```

Set 2 — те же пути под `data/owner_eval/2/`. Отчёт по логу решений:

```bash
uv run python scripts/collect_eval_report.py \
  --log data/tmp/eval_decisions.jsonl \
  --predictions data/owner_eval/1/predictions.jsonl \
  --mapping data/owner_eval/1/mapping.json
```

## 12. Тесты

```bash
uv run pytest tests/ -q          # юнит + API + UI; DB-тесты используют Postgres из шага 7
uv run ruff check src/ tests/
```

## 13. Если что-то не так

| Симптом | Что сделать |
|---|---|
| `DATABASE_URL is not set` | нет `.env` — шаг 6 |
| `connection refused … 5432` | `docker compose up -d`, дождаться `healthy` |
| порт 5432 или 8080 занят | остановить чужой процесс (`ss -ltnp \| grep 5432`) или поменять порт (`--port 8081`; для БД — секция `ports` в `docker-compose.yml` и `DATABASE_URL`) |
| в логе энкодера только `CPUExecutionProvider` при наличии GPU | не экспортирован `LD_LIBRARY_PATH` в этом терминале или стоит CPU-колесо после `uv sync` — шаг 4 «Вариант GPU» |
| `CUDA out of memory` | GPU занят другим процессом (`nvidia-smi`); закрыть его или `compute.device: cpu` |
| PHOCR падает / не качает веса | нет интернета при первом OCR; временно `policy.enable_rerank: false` в `config/ocr_rerank.yaml` (поиск только по изображению) |
| `alembic upgrade head` ругается на размерность 768 | БД от старого энкодера — `VINE_RESET_EMBEDDINGS=1 uv run alembic upgrade head` и индексация (шаг 8) |
| в UI у вин нет рейтинга / блюд | индексация шла без `data/site_database/wines_database_enriched.json` — вернуть файл и повторить шаг 8 |
| ошибка размерности энкодера при старте | в `bin/` не та модель — шаг 5 |
