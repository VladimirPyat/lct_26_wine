# Черновики правил → `.cursor/rules/`

Переход фронта на Jinja2 (Stage 4). Копировать с заменой:

| Черновик | Куда | Что меняется |
|---|---|---|
| `paths-access.mdc` | `.cursor/rules/paths-access.mdc` | п. 5b `src/web/`, 5c `tests/web/`, 5d `agent_docs/design/`; п. 6b — UI-ассеты не в `static/wines/`; п. 10 — Jinja вместо `frontend/` |
| `tooling.mdc` | `.cursor/rules/tooling.mdc` | секция «Frontend (Jinja2)»: `uv add jinja2`, команды тестов/линта, список того, что требует ✅ |
| `frontend-coding.mdc` | `.cursor/rules/frontend-coding.mdc` | React/TS → Jinja: тонкие шаблоны, общий сервисный слой, экранирование, mobile-first, progressive enhancement |
| `frontend-linting.mdc` | `.cursor/rules/frontend-linting.mdc` | ESLint/TS → ruff + (опц.) djlint, `StrictUndefined` |
| `frontend-testing.mdc` | `.cursor/rules/frontend-testing.mdc` | jest/playwright → pytest + TestClient в `tests/web/` |

Без изменений (упоминают `frontend/` как пример, не мешают): `backend-coding.mdc`, `planner-instructions.mdc`, `agents/*.md`, `commands/prune-domain-rules.md`.

```bash
cp agent_docs/drafts/cursor_rules/*.mdc .cursor/rules/
```
