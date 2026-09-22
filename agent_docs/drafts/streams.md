# Потоки разработки (greenfield)

Общий стык: **RankedHit** `{slug, score, wine_id, ...}` и JSONL dump top-K для отладки без полного API.

```
фото → YOLO crop → DINO ONNX → pgvector top-K
                              → Policy (margin / OCR / not_found)
                              → eval slug | UI card
```

| ID | Поток | День 1 без других | Отдаёт |
|----|--------|-------------------|--------|
| **E** | DINO + pgvector | да (после схемы БД) | top-K RankedHit / JSONL |
| **O** | OCR-rerank | да (fuzzy уже в migration) | переставленный top-K |
| **P** | Policy | да на фикстурах JSONL | slug / not_found |
| **V** | Eval HTTP | заглушка slug | совместимость со скриптом |
| **C** | Каталог + доп. поля | да | строки в Postgres |
| **U** | UI | мок | одна карточка |
| **I** | Compose Postgres | да | `DATABASE_URL` |
| **S** | Сомелье | сбоку | retention-фича |

Правило: E не знает FastAPI; P не знает ONNX; S не блокирует точность.

Ежедневный мост E→P: JSONL query → hits. Калибровка τ на `data/owner_eval/`.
