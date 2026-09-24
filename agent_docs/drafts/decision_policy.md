# Политика выдачи (ТЗ)

**Статус:** Stage 2 — стартовые пороги зафиксированы; калибровка только правкой YAML после owner_eval.

## Сценарии (eval)

| Условие | Действие |
|---------|----------|
| `margin = score_1 - score_2` ≥ `margin_min` **или** `enable_rerank: false` | Выдать top-1; OCR не вызывать |
| `margin` < `margin_min` и `enable_rerank: true` | OCR (`IOCREngine`) + fuzzy rerank по top_k → один slug |
| `score_1` < `abs_min` | Флаг **garbage** в логах; для **eval** всё равно отдать лучший slug |

Продуктовый «не найдено» / аналоги — Stage 3 (`enable_not_found_gate`).

## YAML (стартовые значения)

```yaml
policy:
  top_k: 5
  margin_min: 0.1
  abs_min: 0.2
  enable_rerank: true
  # enable_not_found_gate: false   # eval; product later
```

OCR backend: `ocr.engine: phocr | llm` — см. [../contracts/ocr_engine.md](../contracts/ocr_engine.md).

## Eval vs UI

| Контур | При низкой уверенности |
|--------|-------------------------|
| Eval `/v1/eval/predict` | **Всегда** лучший slug; подробности в structured logs + `scripts/collect_eval_report.py` |
| Product UI | Одна карточка или not_found (+ аналоги) — Stage 3 |

## Что берём из старого кода

- Скорер: `text/fuzzy.py` + `normalize.py` + `ocr_postprocess.py`.
- Не берём: inliers-матрицу, found/partial_match/top-3/6, старый `orchestrator.py`.

## Вход политики

Список `RankedHit`: `slug`, `score` (больше = лучше), поля для fuzzy. Score — DINO/pgvector.
