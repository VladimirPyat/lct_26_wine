# План разработки по этапам

**Статус:** Stage 0 выполнен как каркас; детали этапов 1+ — при старте каждого этапа.  
**Стек:** DINO ONNX + Postgres/pgvector + PHOCR + fuzzy OCR-rerank + FastAPI.  
**Перенос:** снимок `_migration/` (gitignore, бэкап). После Stage 0 канонические пути — в дереве репо; к `_migration` не обращаемся без необходимости.  
**Политика выдачи (черновик):** [../drafts/decision_policy.md](../drafts/decision_policy.md).

Приоритет по баллам ТЗ: **точность (50) → фича после поиска (20) → архитектура (15) → дизайн (10) → скорость (5)**.  
Этапы 0–3 обязательны для сдачи ядра; 4 — UI; 5 — если успеем.

---

## Этап 0. Каркас репозитория — DONE

- Скопированы из `_migration`: `src/core/{ocr,text,cropper}`, конфиг-сэмплы, YOLO ONNX → `bin/`, `data/owner_eval/`, TZ → `docs/`, планы/контракты → `agent_docs/`.
- `pyproject` / `uv`, FastAPI `/health`, Compose Postgres+pgvector, `.env.example`, README.
- Правила: `paths-access.mdc`, `tooling.mdc` (без frontend).
- **Не** копировали `eval_organizer/` (харнесс внутри `data/owner_eval/<set>/`).

**Готово когда:** `docker compose up -d` поднимает Postgres; `uvicorn` стартует на CPU.

---

## Этап 1. Подготовка базы и каталога

Контракты: `agent_docs/contracts/wines_schema.md`, `wines_repository.md`, `catalog_prepare.md`.  
Инструкции: `agent_docs/instructions/coder_1_*.md`, `tester_1_*.md`.

### Порядок работ (утверждён)

0. Схема таблиц (Alembic) + lookups  
1. CRUD / slug / vector top-K / filters; тестовая БД 2–3 записи + DINO embeddings (YOLO crop для фикстур не обязателен); unit-тесты  
2. Prepare CSV (ready/additional/rejected + JSON enrich); Compose Postgres; `.env` из example; import ready+additional; SQL-проверки counts  

Точность hit@1 — Этап 2.

**Готово когда:** каталог загружен; CRUD + vector top-K работают на реальных данных; manuals обновлены.

---

## Этап 2. Eval API

- `POST /v1/eval/predict`, multipart `image` → `{"slug":"..."}`.
- Пайплайн: YOLO → DINO → pgvector top-K → policy (margin / OCR-rerank / not_found).
- Харнесс: `data/owner_eval/<set>/participant_test.sh`.

**Готово когда:** `predictions.jsonl`; hit@1 / latency на owner_eval.

---

## Этап 3. Продуктовый поиск (без UI)

- Топ-1 + URL карточки; низкая уверенность → аналоги / not_found.
- Margin/score в API для отладки и питча.

---

## Этап 4. Фронтенд

- Mobile-first; стилистика «Своё Вино».
- В этот момент Planner вернёт `frontend/` в `paths-access` / `tooling`.

---

## Этап 5. Продуктовые фичи (если успеем)

Сомелье → карта магазинов → демо ЛК → опционально админка. Не начинать, пока Stage 2 не даёт приемлемый hit@1.

---

## Зависимости

```
0 каркас ──► 1 каталог ──► 2 eval ──► 3 product API ──► 4 фронт ──► 5 фичи
```

Параллель: скелет 2 на мок-retriever пока идут 1.3–1.5; вёрстка 4 на мок-JSON 3.

---

## Чеклист сдачи

- [ ] Каталог + DINO в pgvector  
- [ ] `/v1/eval/predict` + скрипт заказчика (`data/owner_eval/`)  
- [ ] Продуктовый поиск: карточка или аналоги  
- [ ] UI mobile-first  
- [ ] README + Compose; CPU и GPU  
- [ ] (опционально) сомелье / карта / ЛК  
