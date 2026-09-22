# Политика выдачи (ТЗ)

**Статус:** черновик порогов; числа — после калибровки на DINO + owner_eval.

## Сценарии

| Условие | Действие |
|---------|----------|
| `score_1` высокий и `margin = score_1 - score_2` ≥ τ_margin | Выдать top-1 сразу. OCR-rerank **не обязателен** (можно пропустить для SLA). |
| Несколько близких кандидатов (margin < τ_margin, но score_1 ≥ τ_abs) | Взять top-k → PHOCR + fuzzy rerank → один победитель. |
| Уверенность сильно ниже порога (score_1 < τ_not_found **или** пустой/мусорный кадр) | «Не найдено». |

Пороги `τ_*` и размер k — YAML. Иметь флаги:

```yaml
policy:
  enable_ocr_rerank: true
  enable_not_found_gate: true
  top_k: 20
  rerank_pool: 10
  # dino abs_min / margin_min / not_found_max — TBD
```

Одна точка входа поиска с аргументами/флагами предпочтительнее трёх отдельных пайплайнов (решим при API).

## Eval vs UI

| Контур | При низкой уверенности |
|--------|-------------------------|
| Eval `/v1/eval/predict` | Уточнить: всегда лучший slug (F1 организатора) **или** `null` при not_found. Скрипт принимает оба; метрика у организатора. |
| Product UI | Не сетка «возможно вы искали». Либо одна карточка, либо not_found (+ аналоги из полей каталога — продуктовый плюс). |

## Что берём из старого кода

- Скорер: `text/fuzzy.py` + `normalize.py` + `ocr_postprocess.py`.  
- Не берём: inliers-матрицу, found/partial_match/top-3/6.

## Вход политики

Список `RankedHit`: `slug`, `score` (больше = лучше), `wine_id` / поля для fuzzy. Источник score — DINO/pgvector, не SIFT.
