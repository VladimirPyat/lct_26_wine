# Мануалы

Оглавление человекочитаемой документации. Язык — русский. Политика ведения — `.cursor/rules/documentation.mdc`.

| Файл | Содержание | Кто наполняет |
|------|------------|----------------|
| [quickstart.md](quickstart.md) | Полный запуск с нуля: Docker, драйвер NVIDIA, uv, модели (ссылки), БД, индексация каталога, запуск и открытие UI, продуктовый API, eval, типовые проблемы | @Coder / @BugFixer |
| [user_interface.md](user_interface.md) | Веб-интерфейс: сканер, результат (найдено / низкая уверенность / не найдено), аналоги, карточка, каталог, «Мои вина», заглушки | @Coder / @BugFixer |
| [architecture.md](architecture.md) | Модули, eval-пайплайн, policy / OCR-цепочка, продуктовый поток, аналоги, слой UI | @Coder / @BugFixer |
| [configuration_guide.md](configuration_guide.md) | Энкодер (SigLIP2 fp16), device, policy, OCR, `product.yaml`, LLM tasks, логи (`VINE_LOG_LEVEL`), decision log | @Coder / @BugFixer |
| [manual_testing.md](manual_testing.md) | HITL: owner_eval / API / логи; чеклист UI | @Tester |

Корневой хаб со ссылками: [../README.md](../README.md). Обзор пайплайна по слоям: [../ARCHITECTURE.md](../ARCHITECTURE.md).
