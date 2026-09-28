# Vine Scanner (LCT 2026 / Svoe Vino)

Фото этикетки вина → одна карточка каталога «Своё Вино» с уровнем уверенности (или «не найдено» + аналоги из каталога). Веб-интерфейс для пользователя, eval API организатора и продуктовый JSON API — в одном FastAPI-приложении.

**Стек (кратко):** Python 3.12 / `uv`, FastAPI + Jinja2 (UI без Node/сборки), PostgreSQL + pgvector, Docker Compose (GPU), ONNX Runtime (CUDA / CPU): YOLO (кроп этикетки) + SigLIP2 so400m fp16 (энкодер изображений), PHOCR / LLM (OCR этикетки для спорных случаев).

**Запуск — [manuals/quickstart.md](manuals/quickstart.md).** Коротко (GPU, нужны Docker, драйвер NVIDIA и NVIDIA Container Toolkit; модели в `bin/` и фото в `data/owner_database/images/` — по ссылкам из quickstart):

```bash
export COMPOSE_FILE=docker-compose.full.yml
docker compose build && docker compose up -d db
docker compose run --rm app scripts/rebuild_catalog_db.sh --yes    # база + индексация каталога
docker compose up -d app                                           # http://127.0.0.1:8080/
```

Eval организатора — эндпоинт `http://127.0.0.1:8080/v1/eval/predict`. Интерфейс — [manuals/user_interface.md](manuals/user_interface.md), ручные проверки — [manuals/manual_testing.md](manuals/manual_testing.md).

## Документация

| Документ | Назначение |
|----------|------------|
| [manuals/quickstart.md](manuals/quickstart.md) | Запуск: полный в Docker (GPU) → база + индексация → решение → скрипт заказчика; вариант «только база в Docker» (хост / CPU); подробности |
| [manuals/user_interface.md](manuals/user_interface.md) | Веб-интерфейс: экраны, состояния результата, аналоги, «Мои вина» |
| [manuals/architecture.md](manuals/architecture.md) | Архитектура: модули, пайплайн поиска, policy, аналоги, логи |
| [manuals/configuration_guide.md](manuals/configuration_guide.md) | Настройки (`config/*.yaml`, `.env`, переменные окружения) |
| [manuals/manual_testing.md](manuals/manual_testing.md) | Ручные проверки (HITL) |
| [manuals/index.md](manuals/index.md) | Оглавление мануалов |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Пайплайн и границы слоёв (обзор) |
| [agent_docs/plans/stages.md](agent_docs/plans/stages.md) | Дорожная карта этапов |
| `docs/` | ТЗ и продуктовые требования  |

## Эндпоинты

**Веб-интерфейс** (HTML, подробно — [user_interface.md](manuals/user_interface.md)):

| Метод / путь | Назначение |
|---|---|
| `GET /` | Сканер: камера / загрузка фото |
| `POST /search` | Отправка фото из формы → редирект на результат |
| `GET /result/{search_id}` | Результат поиска (`?analogs=1` — аналоги для найденного вина) |
| `GET /result/{search_id}/photo` | Исходное фото запроса |
| `POST /result/{search_id}/feedback` | «Это то вино? Да / Нет» |
| `GET /wine/{slug}` | Карточка вина |
| `GET /catalog` | Каталог с фильтрами |
| `GET /me` | «Мои вина» (история, избранное, оценки — в браузере) |
| `GET /ui-static/…` | CSS / JS / картинки интерфейса |

**API:**

| Метод / путь | Назначение |
|---|---|
| `GET /health` | Проверка живости |
| `GET /docs` | Swagger UI (OpenAPI) |
| `GET /static/wines/{slug}.webp` | Фото бутылок каталога |
| `POST /v1/eval/predict` | Eval организатора: multipart `image` → `{"slug": "..."}` |
| `POST /api/v1/search` | Фото → карточка вина, уверенность, top-5, аналоги |
| `GET /api/v1/search/{search_id}` | Сохранённый результат поиска |
| `GET /api/v1/search/{search_id}/analogs` | Аналоги (`?limit=5`) |
| `GET /api/v1/wines` | Каталог по фильтрам (`color`, `grape`, `region`, `sweetness`, `dish`, `exclude_manufacturer`, `limit`, `offset`) |
| `GET /api/v1/wines/{slug}` | Карточка вина |
| `GET /api/v1/dictionaries` | Справочники фильтров |
| `POST /api/v1/feedback` | Отзыв «то / не то вино» |

Примеры `curl` — [manuals/quickstart.md](manuals/quickstart.md#10-продуктовый-api-apiv1).

## Структура репозитория

| Путь | Назначение |
|------|------------|
| `src/api/` | FastAPI: приложение (`main.py`), рантайм моделей, eval-пайплайн, роутеры `eval` / `product` |
| `src/core/` | Ядро: кроп (YOLO), энкодер + поиск (pgvector), policy, OCR, продуктовый сервис (`core/product`) |
| `src/db/` | SQLAlchemy-модели, репозиторий, импорт каталога |
| `src/llm/` | LLM-клиент, задачи и промпты (OCR через LLM) |
| `src/web/` | Веб-интерфейс: роутер, view-модели, шаблоны Jinja2, статика |
| `config/` | YAML-настройки (модели, устройство, policy/OCR, продукт) |
| `alembic/` | Миграции схемы БД |
| `scripts/` | Индексация каталога (`rebuild_catalog_db.sh`, `catalog_import.py`), калибровка, очистка, отчёты eval |
| `scripts/catalog_prepare/` | Подготовка CSV каталога и сверка ассетов |
| `tests/`, `tests/web/` | Автотесты (pytest): ядро, API, UI |
| `bin/` | ONNX-модели (не в git — ссылки в quickstart) |
| `data/wines_integrated_updated.csv` | Список вин, по которому собрана БД (в git) |
| `data/wines_problem_images.csv` | Список проблемных фото: мелкие (часть заменена на крупные) и отсутствующие (в git) |
| `data/site_database/wines_database_enriched.json` | Данные сайта: рейтинг, блюда, ссылки (в git) |
| `data/owner_database/images/` | Фото бутылок `{slug}.webp` для индексации (не в git — облако) |
| `data/owner_eval/` | Eval-набор организатора (не в git) |
| `data/tmp/` | Рабочие файлы: кропы, фото запросов (10 дней), логи решений и отзывов (не в git) |
| `static/wines/` | Фото бутылок для UI, создаются индексацией (не в git) |
| `manuals/` | Человекочитаемые мануалы |
| `agent_docs/` | Планы, контракты, инструкции, прогресс, отчёты |
| `docs/` | Требования (ТЗ) |
| `Dockerfile` | Образ приложения (GPU: onnxruntime-gpu + CUDA 13 / cuDNN 9 pip-колёсами) |
| `docker-compose.full.yml` | Полный запуск: Postgres + приложение на GPU (основной способ) |
| `docker-compose.yml` | Только PostgreSQL + pgvector (приложение на хосте, разработка / CPU) |
