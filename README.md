# Vine Scanner (LCT 2026 / Svoe Vino)

Фото этикетки вина → одна карточка каталога (или `not_found` + аналоги). API, совместимый с eval организатора — на более поздних этапах.

**Стек (кратко):** Python 3.11+ / `uv`, FastAPI, PostgreSQL + pgvector, SigLIP2 (энкодер изображений) + YOLO ONNX, PHOCR (подключение по этапам).

## Документация

| Документ | Назначение |
|----------|------------|
| [manuals/index.md](manuals/index.md) | Оглавление мануалов |
| [manuals/quickstart.md](manuals/quickstart.md) | Быстрый запуск |
| [manuals/architecture.md](manuals/architecture.md) | Архитектура системы |
| [manuals/configuration_guide.md](manuals/configuration_guide.md) | Настройки и профили |
| [manuals/manual_testing.md](manuals/manual_testing.md) | Ручные проверки (HITL), Stage 2 |
| [agent_docs/plans/stages.md](agent_docs/plans/stages.md) | Дорожная карта этапов |
| `docs/` | ТЗ и продуктовые требования (read-only для агентов) |


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
