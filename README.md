# Vine Scanner (LCT 2026 / Svoe Vino)

Фото этикетки вина → одна карточка каталога (или `not_found` + аналоги). API совместим с eval организатора; продуктовый JSON API — `/api/v1/*`.

**Стек (кратко):** Python 3.11+ / `uv`, FastAPI, PostgreSQL + pgvector, SigLIP2 (энкодер изображений) + YOLO ONNX, PHOCR (подключение по этапам).

## Документация

| Документ | Назначение |
|----------|------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Пайплайн и границы слоёв (обзор) |
| [manuals/index.md](manuals/index.md) | Оглавление мануалов |
| [manuals/quickstart.md](manuals/quickstart.md) | Быстрый запуск |
| [manuals/architecture.md](manuals/architecture.md) | Архитектура: детали модулей, policy, логов |
| [manuals/configuration_guide.md](manuals/configuration_guide.md) | Настройки и профили |
| [manuals/manual_testing.md](manuals/manual_testing.md) | Ручные проверки (HITL), Stage 2 |
| [agent_docs/plans/stages.md](agent_docs/plans/stages.md) | Дорожная карта этапов |
| `docs/` | ТЗ и продуктовые требования (read-only для агентов) |

## Эндпоинты

| Метод / путь | Назначение |
|---|---|
| `GET /health` | Проверка живости |
| `GET /static/wines/{slug}.webp` | Картинки каталога |
| `POST /v1/eval/predict` | Eval организатора: multipart `image` → `{"slug": "..."}` |
| `POST /api/v1/search` | Фото → карточка вина, уверенность, top-5, аналоги |
| `GET /api/v1/search/{search_id}` | Сохранённый результат поиска |
| `GET /api/v1/search/{search_id}/analogs` | Аналоги (`?limit=5`) |
| `GET /api/v1/wines` | Каталог по фильтрам (`color`, `grape`, `region`, `sweetness`, `dish`, `exclude_manufacturer`, `limit`, `offset`) |
| `GET /api/v1/wines/{slug}` | Карточка вина |
| `GET /api/v1/dictionaries` | Справочники фильтров |
| `POST /api/v1/feedback` | Отзыв «то / не то вино» |

Примеры `curl` — [manuals/quickstart.md](manuals/quickstart.md#продуктовый-api-apiv1).


## Layout

| Path | Role |
|------|------|
| `src/` | FastAPI + core |
| `config/` | YAML-настройки |
| `bin/` | ONNX-веса |
| `data/owner_eval/` | Eval harness организатора |
| `data/owner_database/`, `data/site_database/` | Источники каталога (SSOT) |
| `scripts/catalog_prepare/` | Prepare CSV (ready/additional/rejected) |
| `static/wines/` | Картинки каталога после import |
| `docs/` | Требования |
| `agent_docs/` | Планы, контракты, инструкции, прогресс |
| `manuals/` | Человекочитаемые мануалы |
| `_migration/` | Gitignored backup — не часть рабочего потока после Stage 0 |
