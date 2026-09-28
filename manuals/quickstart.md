# Быстрый запуск

Сначала — короткое руководство: всё в Docker на GPU (Linux или Windows). Дальше — вариант «в Docker только база, приложение на хосте» (в том числе без GPU) и подробности. Описание экранов — [user_interface.md](user_interface.md), ручные проверки — [manual_testing.md](manual_testing.md), настройки — [configuration_guide.md](configuration_guide.md).

---

## Часть 1. Полный запуск в Docker (GPU)

В `docker-compose.full.yml` два сервиса: `db` (PostgreSQL + pgvector) и `app` (FastAPI: веб-интерфейс, eval API организатора и продуктовый API в одном процессе, GPU). Модели, фото каталога и данные подключаются в контейнер из папок репозитория.

### 1.1. Что нужно на машине

| Что | Где взять |
|---|---|
| Docker + Docker Compose v2 | Linux: [Install Docker Engine](https://docs.docker.com/engine/install/); Windows: [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/) с бэкендом WSL2 |
| Драйвер NVIDIA ≥ 580 (CUDA 13) | [nvidia.com/drivers](https://www.nvidia.com/drivers); проверка: `nvidia-smi` → `CUDA Version: 13.x` |
| Доступ контейнеров к GPU | Linux: **NVIDIA Container Toolkit** (ниже); Windows: ничего дополнительно — Docker Desktop + WSL2 пробрасывает GPU сам ([GPU support in Docker Desktop](https://docs.docker.com/desktop/features/gpu/)) |
| ~15 ГБ диска, интернет при первом запуске | образ (~6 ГБ с библиотеками CUDA), модели ~0.9 ГБ, фото ~0.15 ГБ, веса PHOCR ~270 МБ (качаются при первом старте приложения) |

CUDA Toolkit ставить **не нужно**: библиотеки CUDA 13 / cuDNN 9 уже внутри образа.

**NVIDIA Container Toolkit (Linux).** Официальная инструкция: [Installing the NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html). Для Ubuntu / Debian:

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker
```

Проверка (Linux и Windows): `docker run --rm --gpus all ubuntu nvidia-smi` — должна показаться видеокарта.

### 1.2. Код, модели, фото каталога

```bash
git clone <URL репозитория> lct_vine_final
cd lct_vine_final
```

**Модели → `bin/`** (скачать в браузере, сохранить с этими именами):

| Файл | Ссылка | Запасная ссылка |
|---|---|---|
| `bin/yolo_detect_labels_2.onnx` (~12 МБ, детектор этикетки) | [Google Drive](https://drive.google.com/file/d/1uKGYwkL7Ycm5QMgsWDl5KrTOpwwtCrtg/view?usp=drive_link) | [Google Drive (alt)](https://drive.google.com/file/d/1fZhse4rYECP1jjcPX2TwDg7lTK2l9dTU/view?usp=drive_link) |
| `bin/siglip2_wine_p1_epoch_3_fp16.onnx` (~817 МБ, энкодер изображений) | [Google Drive](https://drive.google.com/file/d/1zVKvqYtkcNy-_OF8mIKMl_RVp-HHhOqK/view?usp=drive_link) | [Google Drive (alt)](https://drive.google.com/file/d/1wSSgStfcpW-JXLJvtdpUQAcWGXMQ8RoH/view?usp=drive_link) |

**Фото каталога → `data/owner_database/images/`**: папка [images (Google Drive)](https://drive.google.com/drive/folders/1HYiy0he8OdAui_56cIZ8xUhYXN-mJo81?usp=drive_link) → «Скачать» (zip) → распаковать так, чтобы 2091 файл `{slug}.webp` лежал прямо в `data/owner_database/images/`. Список вин и данные сайта уже в репозитории (см. [3.1](#31-данные-каталога)).

**Опционально — `.env`:** `cp .env.example .env` (ключ `QWEN_API_KEY` нужен только для OCR через LLM; на GPU используется локальный PHOCR). Файл не обязателен.

### 1.3. Создание базы

Чтобы не повторять `-f docker-compose.full.yml` в каждой команде:

```bash
export COMPOSE_FILE=docker-compose.full.yml           # Linux / WSL / Git Bash
# $env:COMPOSE_FILE = "docker-compose.full.yml"      # Windows PowerShell
```

```bash
docker compose build                                   # образ приложения (первый раз ~5–10 мин)
docker compose up -d db                                # PostgreSQL + pgvector
docker compose run --rm app scripts/rebuild_catalog_db.sh --yes   # схема + индексация каталога
```

Индексация: YOLO вырезает этикетку с каждого фото → SigLIP2 кодирует → векторы в БД; полные фото бутылок → `static/wines/` (их показывает интерфейс). На GPU — ~10 минут (RTX 3070 Laptop); 10 фото без найденной этикетки кодируются целиком — это нормально. В конце скрипт пишет `done.`, проверка:

```bash
docker compose exec db psql -U vine -d vine -c "SELECT count(*), count(embedding) FROM wines;"
# 2091 | 2091
```

### 1.4. Запуск решения

```bash
docker compose up -d app
docker compose logs -f app          # дождаться "Uvicorn running on http://0.0.0.0:8080", выход — Ctrl+C
```

В логе старта: `Encoder ONNX model=siglip2_wine_p1_epoch_3_fp16.onnx providers=['CUDAExecutionProvider', ...]`, `OCR engine: configured=phocr effective=phocr reason=cuda_available`, затем `PHOCR ready`. При **первом** старте перед `PHOCR ready` качаются веса PHOCR (~270 МБ, до пары минут; дальше они лежат в томе `phocr_models`) — сервер начинает отвечать только после этого, поэтому скрипт заказчика запускать после `Uvicorn running`. Проверка: `curl http://127.0.0.1:8080/health` → `{"status":"ok"}`.

Порт по умолчанию — `8080`; другой: `VINE_PORT=8090 docker compose up -d app`.

### 1.5. Скрипт заказчика (eval)

Эндпоинт для скрипта: **`http://127.0.0.1:8080/v1/eval/predict`** (multipart-поле `image` → `{"slug": "..."}`).

Скрипт — bash, нужны `curl`, `jq`, `awk`. На Windows запускать из WSL (Ubuntu): `localhost` там ведёт в Docker Desktop.

```bash
./participant_test.sh \
  --images-dir ./queries \
  --manifest ./queries.tsv \
  --endpoint 'http://127.0.0.1:8080/v1/eval/predict' \
  --output ./predictions.jsonl
```

Файл `--output` не должен существовать (скрипт не перезаписывает его и завершится с `ERROR: output already exists`). На GPU один запрос — ~0.3–1.6 с.

Пример на публичных наборах (если лежат в `data/owner_eval/`): те же флаги с путями `./data/owner_eval/1/queries`, `./data/owner_eval/1/queries.tsv`; set 2 — `data/owner_eval/2/`.

### 1.6. Интерфейс и ручная проверка

- Интерфейс: [http://127.0.0.1:8080/](http://127.0.0.1:8080/) — экраны и сценарии: [user_interface.md](user_interface.md).
- Swagger (JSON API): [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs), примеры — [часть 3.3](#33-продуктовый-api-apiv1).
- Ручная проверка: [manual_testing.md](manual_testing.md).

Камера на телефоне работает только по HTTPS или на `localhost`; по `http://<IP-компьютера>:8080` доступна загрузка фото из галереи.

### 1.7. Остановка и обновление

```bash
docker compose down                 # остановить (БД и веса PHOCR сохраняются в томах)
docker compose up -d --build app    # после обновления кода
docker compose down -v              # полный сброс: удаляет БД — потом снова 1.3
```

---

## Часть 2. В Docker только база, приложение на хосте

Подходит для разработки и для машины **без GPU** (приложение работает на CPU, медленнее: ~1 с на запрос против ~0.15 с). Нужны Linux/WSL (или macOS для CPU), Docker, [uv](https://docs.astral.sh/uv/getting-started/installation/). Используется обычный `docker-compose.yml` (только Postgres, порт 5432 на хосте) — это отдельная БД, не та, что в части 1.

### 2.1. Окружение

```bash
uv python install 3.12
uv sync --python 3.12 --extra ml --extra db --extra dev
cp .env.example .env              # DATABASE_URL=postgresql+psycopg://vine:vine@127.0.0.1:5432/vine
```

**GPU на хосте** (нужен только драйвер NVIDIA ≥ 580; CUDA Toolkit и Container Toolkit не нужны):

```bash
uv pip uninstall onnxruntime
uv pip install -r requirements-gpu.txt
# в КАЖДОМ терминале перед запуском / индексацией:
export LD_LIBRARY_PATH="$(pwd)/.venv/lib/python3.12/site-packages/nvidia/cu13/lib:$(pwd)/.venv/lib/python3.12/site-packages/nvidia/cudnn/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
uv run python -c "import onnxruntime as o; print(o.get_available_providers())"   # есть CUDAExecutionProvider
```

После GPU-overlay не запускайте `uv sync` (вернёт CPU-колесо); `uv run …` безопасен.

**CPU:** в `config/compute_cropper.yaml` поставить `compute.device: cpu`. OCR без CUDA переключается на LLM (нужен `QWEN_API_KEY` в `.env`), без ключа работает без OCR (поиск только по изображению). Итог выбора — строка `OCR engine: …` в логе старта.

Модели и фото — как в [1.2](#12-код-модели-фото-каталога).

### 2.2. База и индексация

```bash
docker compose up -d && docker compose ps       # healthy
scripts/rebuild_catalog_db.sh --yes              # схема + индексация (на CPU заметно дольше)
docker compose exec db psql -U vine -d vine -c "SELECT count(*), count(embedding) FROM wines;"   # 2091 | 2091
```

### 2.3. Запуск

```bash
uv run uvicorn api.main:app --app-dir src --host 0.0.0.0 --port 8080
```

Дальше — как в [1.5](#15-скрипт-заказчика-eval) и [1.6](#16-интерфейс-и-ручная-проверка). Остановка — `Ctrl+C`, база — `docker compose down`.

Тесты: `uv run pytest tests/ -q` (DB-тесты используют эту Postgres), линт — `uv run ruff check src/ tests/`.

---

## Часть 3. Подробности

### 3.1. Данные каталога

| Что | Где | В git |
|---|---|---|
| Список вин, по которому собрана БД (2103 вина) | `data/wines_integrated_updated.csv` | да |
| Данные сайта: рейтинг, блюда, ссылка на страницу, крепость, температура подачи | `data/site_database/wines_database_enriched.json` | да |
| Список проблемных фото | `data/wines_problem_images.csv` | да |
| Фото бутылок `{slug}.webp` (2091 файл, ~130 МБ) | `data/owner_database/images/` | нет — [облако](https://drive.google.com/drive/folders/1HYiy0he8OdAui_56cIZ8xUhYXN-mJo81?usp=drive_link) |

Часть совсем мелких фото (меньше 200 px) заменена на более крупные. Список приложен — `data/wines_problem_images.csv` (100 строк): 88 — мелкие фото (из них 7 ещё и дубли чужого фото), 12 — вина без фото (нет ни фото, ни страницы на сайте). Эти 12 в индекс не попадают: 2103 − 12 = 2091 вино в БД.

Распаковка zip из Google Drive (Linux / WSL):

```bash
mkdir -p data/owner_database/images /tmp/vine_images
for z in ~/Downloads/images-*.zip; do unzip -o "$z" -d /tmp/vine_images; done
find /tmp/vine_images -name '*.webp' -exec mv -t data/owner_database/images/ {} +
ls data/owner_database/images | wc -l        # 2091
```

Модели из консоли (опционально): `uvx gdown --fuzzy '<ссылка на файл>' -O bin/<имя файла>`. Пути в конфиге: `config/compute_cropper.yaml` → `yolo_model_path`, `config/database.yaml` → `dino_model_path` (`embedding_dim: 1152`); при несовпадении размерности приложение падает при старте с понятной ошибкой.

### 3.2. Что делает индексация (`scripts/rebuild_catalog_db.sh --yes`)

`--yes` обязателен: таблица `wines` очищается и заливается заново.

1. **CSV** — список вин + данные сайта → `scripts/catalog_prepare/wines_clean_ready.csv` (отбракованные — `wines_clean_rejected.csv`).
2. **Ассеты** — YOLO вырезает этикетку → `data/tmp/catalog_crops/` (кодируется в БД); полные бутылки → `static/wines/` (показывает UI). Сверка — `data/tmp/catalog_assets_check.csv`; старые ассеты уезжают в `.trash/`.
3. **БД** — `alembic upgrade head` (с `VINE_RESET_EMBEDDINGS=1`), кодирование SigLIP2 и вставка; фото, где YOLO не нашёл этикетку, кодируются целиком.

Раздельно: `--prepare-only` (шаги 1–2, БД не трогается), затем `--yes --reuse-assets` (шаг 3). Меньше видеопамяти — `-- --encode-batch-size 8`. В Docker все команды — через `docker compose run --rm app scripts/rebuild_catalog_db.sh …`.

### 3.3. Продуктовый API (`/api/v1`)

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

Рабочие файлы (в `data/tmp/`, в Docker — та же папка через том): фото запросов и JSON результатов — `search_queries/` (10 дней), отзывы — `search_feedback.jsonl`, лог решений — `eval_decisions.jsonl`. Чистка по сроку — при старте и `scripts/cleanup_search_queries.py [--dry-run] [--days N]`. Отчёт по eval: `uv run python scripts/collect_eval_report.py --log data/tmp/eval_decisions.jsonl --predictions <predictions.jsonl> --mapping <mapping.json>`.

### 3.4. Логи

Приложение пишет логи в stderr (`docker compose logs app` или терминал uvicorn). Уровень — `VINE_LOG_LEVEL` (`DEBUG` / `INFO` / `WARNING`, по умолчанию `INFO`); в Docker — строкой `VINE_LOG_LEVEL=DEBUG` в `.env`.

### 3.5. Если что-то не так

| Симптом | Что сделать |
|---|---|
| `could not select device driver "nvidia"` / `unknown or invalid runtime name: nvidia` | не установлен / не настроен NVIDIA Container Toolkit (1.1), после настройки — `sudo systemctl restart docker` |
| в логе энкодера только `CPUExecutionProvider` | Docker: контейнер без GPU — проверить `docker run --rm --gpus all ubuntu nvidia-smi`; хост: не экспортирован `LD_LIBRARY_PATH` или вернулось CPU-колесо после `uv sync` (2.1) |
| `CUDA out of memory` | GPU занят другим процессом (`nvidia-smi`) — закрыть его |
| порт 8080 занят | `VINE_PORT=8090 docker compose up -d app` (хост: `--port 8090`) |
| `DATABASE_URL is not set` (хост) | нет `.env` — 2.1 |
| `connection refused … 5432` (хост) | `docker compose up -d`, дождаться `healthy` |
| пустой каталог / 503 на поиске | не выполнена индексация (1.3 / 2.2) или нет фото в `data/owner_database/images/` |
| в UI у вин нет рейтинга / блюд | индексация шла без `data/site_database/wines_database_enriched.json` — вернуть файл и повторить индексацию |
| ошибка размерности энкодера при старте | в `bin/` не та модель — 1.2 |
| PHOCR не качает веса (`PHOCR warm-up failed` в логе) | нет интернета при первом старте; временно `policy.enable_rerank: false` в `config/ocr_rerank.yaml` (поиск только по изображению) |
| `alembic upgrade head` ругается на размерность 768 | БД от старого энкодера — индексация `rebuild_catalog_db.sh --yes` (сама сбрасывает эмбеддинги) |
