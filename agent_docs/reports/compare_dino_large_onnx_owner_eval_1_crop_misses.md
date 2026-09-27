# DINOv2-large P1 ONNX + YOLO crop — miss@5 cards (owner_eval set1)

**Model tag:** `dinov2_large_wine_phase1`  
**Scored:** 27  ·  **Hit@5:** 26  ·  **Miss@5:** 1  ·  **R@5:** 0.963

Slug meta from `data/owner_database/wines_integrated_updated.csv` (name · winery · color · grape · category).

---

## Aggregates on miss queries (top-k slots)

| relation | slots |
|----------|------:|
| `same_winery` | 5 |

### Frequent intruders (appear in miss top-k, not GT)

| n | file | winery (from CSV) |
|--:|------|-------------------|
| 1 | `b-yu-rne-krasnostop-suhoe-krasnoe-classic.webp` | Винодельня Бюрнье |
| 1 | `b-yu-rne-malbek-krasnoe-suhoe.webp` | Винодельня Бюрнье |
| 1 | `b-yu-rne-sira-krasnoe-suhoe-classic.webp` | Винодельня Бюрнье |
| 1 | `vinodelnya-byurne-kaberne-sovinon-krasnoe-suhoe-135.webp` | Винодельня Бюрнье |
| 1 | `b-yu-rne-pino-gri-pozdnij-sbor-sladkoe-beloe.webp` | Винодельня Бюрнье |

### Intruder wineries

| n | winery |
|--:|--------|
| 5 | Винодельня Бюрнье |

### Color GT → top candidate

| n | pattern |
|--:|---------|
| 2 | Интенсивный рубиновый → Насыщенный рубиновый |
| 1 | Интенсивный рубиновый → Гиперинтенсивный пурпурный |
| 1 | Интенсивный рубиновый → Глубокий темно-рубиновый |
| 1 | Интенсивный рубиновый → Насыщенный золотистый |

### Winery GT → top candidate

| n | pattern |
|--:|---------|
| 5 | Винодельня Бюрнье → Винодельня Бюрнье |

---

## Miss cards (rank > 5)

### `e3f116c0.jpeg` — rank **8**

**GT:** `vinodelnya-byurne-merlo-krasnoe-suhoe-14.webp`  
БЮРНЬЕ.МЕРЛО сухое красное · Винодельня Бюрнье · Интенсивный рубиновый · Мерло · Красное

gap12=0.00861668586730957 · same_winery_in_top=5 · same_color_in_top=0 · same_category_in_top=4

| # | relation | file | name | winery | color | grape | category |
|--:|----------|------|------|--------|-------|-------|----------|
| 1 | `same_winery` | `b-yu-rne-krasnostop-suhoe-krasnoe-classic.webp` | БЮРНЬЕ.КРАСНОСТОП сухое красное Classic | Винодельня Бюрнье | Насыщенный рубиновый | Красностоп | Красное |
| 2 | `same_winery` | `b-yu-rne-malbek-krasnoe-suhoe.webp` | БЮРНЬЕ.МАЛЬБЕК красное сухое | Винодельня Бюрнье | Гиперинтенсивный пурпурный | Мальбек | Красное |
| 3 | `same_winery` | `b-yu-rne-sira-krasnoe-suhoe-classic.webp` | БЮРНЬЕ.СИРА красное сухое Classic | Винодельня Бюрнье | Насыщенный рубиновый | Сира | Красное |
| 4 | `same_winery` | `vinodelnya-byurne-kaberne-sovinon-krasnoe-suhoe-135.webp` | БЮРНЬЕ.КАБЕРНЕ СОВИНЬОН сухое красное | Винодельня Бюрнье | Глубокий темно-рубиновый | Каберне Совиньон | Красное |
| 5 | `same_winery` | `b-yu-rne-pino-gri-pozdnij-sbor-sladkoe-beloe.webp` | БЮРНЬЕ.ПИНО ГРИ Поздний сбор сладкое белое | Винодельня Бюрнье | Насыщенный золотистый | Пино Гри | Белое |

---

## Training signals (heuristic)

- High `same_winery` in miss tops → need stronger **within-winery** separation (margin / hard same-winery negatives).
- High `other` + same color/category → **lookalike packaging / line twins** across producers; near-cluster or hard-FAR mining.
- Color flips (e.g. red GT → white/sparkling tops) → preprocess / label noise / weak visual cue; check query crop quality before changing loss.
