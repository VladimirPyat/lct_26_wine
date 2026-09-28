# Мануалы

Оглавление человекочитаемой документации. Язык — русский. Политика ведения — `.cursor/rules/documentation.mdc`.

| Файл | Статус | Кто наполняет |
|------|--------|----------------|
| [architecture.md](architecture.md) | Stage 2 — LLM + eval pipeline + policy (SigLIP2, confident rerank); Stage 4 — слой веб-интерфейса | @Coder / @BugFixer |
| [configuration_guide.md](configuration_guide.md) | Stage 2 — энкодер SigLIP2, policy, ocr.engine, LLM tasks, log | @Coder / @BugFixer |
| [quickstart.md](quickstart.md) | Stage 2B — uvicorn + owner_eval + перезаливка каталога; Stage 4 — запуск UI, HTTPS для камеры | @Coder / @BugFixer |
| [manual_testing.md](manual_testing.md) | Stage 2B — HITL owner_eval / API / logs; Stage 4 — заготовка чеклиста UI | @Tester |

Корневой хаб со ссылками: [../README.md](../README.md). Обзор пайплайна по слоям: [../ARCHITECTURE.md](../ARCHITECTURE.md).
