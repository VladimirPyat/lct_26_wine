# Отчёт: Stage 2B Eval API + owner_eval

**Роль:** @Tester (`tester_2b_eval.md`)  
**Дата:** 2026-09-24  
**Вердикт:** **TEST_PASS** (с зафиксированными дефектами / soft-notes)

## Контекст

- Progress: `READY_FOR_TEST` (2B); phocr UNBLOCKED (`phocr>=1.0.3` + numpy override).
- Каталог: 1950 вин; Postgres Compose healthy.
- Primary e2e: `ocr.engine=phocr`, `enable_rerank=true`.
- Перед прогоном докачан отсутствующий вес `ru_rec_decoder_v1.onnx` (modelscope timeout на первом init).

## Unit / API

| ID | Кейс | Результат |
|----|------|-----------|
| 2B-01 | Большой margin → OCR не вызывается | PASS |
| 2B-02 | Малый margin + enable_rerank → OCR (mock) | PASS |
| 2B-03 | `enable_rerank=false` → OCR никогда | PASS |
| 2B-04 | `abs_min` garbage → флаг + slug top-1 | PASS |
| 2B-05 | HTTP multipart → `{"slug":...}` 200 | PASS |
| 2B-05b | Пустой upload → 400 | PASS |
| 2B-07 | Canary swapped golden → hit@1 ≈ 0 | PASS |

Тесты: `tests/test_policy_decision.py`, `tests/test_eval_predict_api.py`, `tests/test_owner_eval_scoring.py`, helper `tests/owner_eval_scoring.py`.

## Owner eval e2e

| Set | Harness exit | preds / nulls | hit@1 | rerank_rate | garbage_rate | latency p50 / p95 (ms) |
|-----|--------------|---------------|-------|-------------|--------------|-------------------------|
| 1 | 0 | 27 / 0 | **0.5556 (15/27)** | 0.778 | 0.000 | **5033 / 8889** |
| 2 | 0 | 25 / 0 | **0.7200 (18/25)** | 0.800 | 0.040 | **6016 / 8405** |

- Логи: `data/tmp/eval_decisions_set1.jsonl`, `data/tmp/eval_decisions_set2.jsonl`
- Predictions: `data/owner_eval/{1,2}/predictions.jsonl`
- Отчёты: `data/tmp/eval_report_set{1,2}.json` (через **плоский** mapping)
- Soft latency ~3s: **не достигнуто** на CPU + phocr (p50 ≈ 5–6 s). Не код-баг; калибровка / железо.

### Anti-cheat

Честный golden vs mapping → hit@1 = 1.0; permute slugs → hit@1 < 0.15. Компаратор валиден. Файл `predictions.golden.jsonl` не изменялся.

## Команды и exit codes

```text
docker compose up -d                         → 0
uv sync --extra ml --extra db --extra dev    → 0
uv run alembic upgrade head                  → 0
uv run uvicorn … :8080                       → started (PID shell 802768)
participant_test.sh set1                     → SET1_EXIT:0 (~132 s)
participant_test.sh set2                     → SET2_EXIT:0 (~133 s)
collect_eval_report.py set1/set2 (flat map)  → 0
uv run pytest tests/ -v -k "eval or policy or predict" → 10 passed, exit 0
uv run ruff check src/ tests/                → 0
```

## Дефекты (для @Coder, не чинились Tester’ом)

1. **`scripts/collect_eval_report.py` / `load_mapping`** не понимает organizer `mapping.json` с `cases[].expected_slug`. Сырой `--mapping data/owner_eval/1/mapping.json` → `hit@1: n/a` (маппит только строковые top-level ключи вроде `source_dir`). Workaround: плоский JSON `{query_id: slug}` (см. `manuals/manual_testing.md`).
2. **Latency soft ~3s** не выдержан при phocr + rerank на CPU (p50 5–6s, p95 ~8–9s). Предложение: измерить `enable_rerank=false` baseline; не тюнить YAML в рамках этого PASS.
3. **Первый старт PHOCR** падал без `ru_rec_decoder_v1.onnx` (timeout modelscope). После докачки в site-packages — OK. Документировать в configuration/quickstart при необходимости.

## HITL

Заполнен `manuals/manual_testing.md`; статус в `manuals/index.md` обновлён.

## Next

- Stage 2B: sign-off / threshold tuning по желанию владельца.
- @Coder: починить `load_mapping` под `cases` (дефект 1).
