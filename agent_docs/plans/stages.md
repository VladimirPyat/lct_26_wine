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

## Этап 2. Eval API + LLM

Контракты (Phase A draft): `llm_engine.md`, `ocr_engine.md`, `eval_predict.md`.  
Подэтапы **независимы** при готовых контрактах.

### 2A. LLM foundation

- OpenAI-compatible клиент; task YAML под `src/llm/tasks/` с **inline** provider (без registry).
- `.env` — только API-ключи; `retries` default 3; factory `create_llm_engine(task_name)`.
- Первая задача: `ocr_label` → `list[str]` через `IOCREngine` adapter.

### 2B. Eval API

- `POST /v1/eval/predict`, multipart `image` → **всегда** `{"slug":"..."}`.
- Пайплайн: YOLO → DINO → pgvector `top_k=5` → policy (`margin_min=0.1`, `abs_min=0.2`, `enable_rerank`).
- OCR: `phocr` \| `llm`; fuzzy rerank на shortlist; structured logs + `scripts/collect_eval_report.py`.
- Харнесс: `data/owner_eval/<set>/participant_test.sh` (set1, затем set2).

**Готово когда:** set1/set2 `predictions.jsonl`; hit@1 / latency в отчёте; anti-cheat swapped golden падает.

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
0 каркас ──► 1 каталог ──► 2A LLM ┐
                      └──────────► 2B eval ──► 3 product API ──► 4 фронт ──► 5 фичи
```

Параллель: 2A ∥ 2B(phocr); 2B с `ocr.engine=llm` после 2A; вёрстка 4 на мок-JSON 3.

---

Оптимизации «на потом»: [backlog.md](backlog.md) (батч DINO import, YOLO CUDA для bulk crop).

## Чеклист сдачи

- [ ] Каталог + DINO в pgvector  
- [ ] LLM task layer (2A) + `/v1/eval/predict` + скрипт заказчика (`data/owner_eval/`)  
- [ ] Продуктовый поиск: карточка или аналоги  
- [ ] UI mobile-first  
- [ ] README + Compose; CPU и GPU  
- [ ] (опционально) сомелье / карта / ЛК  
