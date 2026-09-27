# DINOv2-large P3 ONNX + YOLO crop — miss@5 cards (owner_eval set2)

**Model tag:** `dinov2_large_wine_phase3`  
**Scored:** 24  ·  **Hit@5:** 23  ·  **Miss@5:** 1  ·  **R@5:** 0.958

Slug meta from `data/owner_database/wines_integrated_updated.csv` (name · winery · color · grape · category).

---

## Aggregates on miss queries (top-k slots)

| relation | slots |
|----------|------:|
| `other` | 4 |
| `same_winery` | 1 |

### Frequent intruders (appear in miss top-k, not GT)

| n | file | winery (from CSV) |
|--:|------|-------------------|
| 1 | `golubitskoe-estate-merlo-krasnoe-suhoe-135.webp` | Golubitskoe Estate |
| 1 | `golubitskoe-estate-kaberne-sovinon-krasnoe-suhoe-137.webp` | Golubitskoe Estate |
| 1 | `golubitskoe-estate-sovinon-blan-beloe-suhoe-11.webp` | Golubitskoe Estate |
| 1 | `golubitskoe-estate-chardonnay.webp` | Поместье Голубицкое |
| 1 | `golubitskoe-estate-risling.webp` | Golubitskoe Estate |

### Intruder wineries

| n | winery |
|--:|--------|
| 4 | Golubitskoe Estate |
| 1 | Поместье Голубицкое |

### Color GT → top candidate

| n | pattern |
|--:|---------|
| 2 | Светло-розовое → Светло-соломенный |
| 1 | Светло-розовое → Темно-рубиновый |
| 1 | Светло-розовое → Темно-рубиновый с гранатовым ободком |
| 1 | Светло-розовое → Золотисто-соломенный |

### Winery GT → top candidate

| n | pattern |
|--:|---------|
| 4 | Поместье Голубицкое → Golubitskoe Estate |
| 1 | Поместье Голубицкое → Поместье Голубицкое |

## GT missing from gallery

- `a0c040fc.jpg` → `skalistyy-bereg-veter-v-travah-kaberne-fran-krasnoe-suhoe-13.webp`  
  Ветер в травах · Скалистый берег · Светло-вишневый · Каберне Совиньон, Каберне Фран, Мерло · Красное

---

## Miss cards (rank > 5)

### `9b891f99.jpg` — rank **6**

**GT:** `golubitskoe-rose.webp`  
Golubitskoe Rose · Поместье Голубицкое · Светло-розовое · Каберне Совиньон, Мерло, Пино Гриджио, Пино Нуар · Розовое

gap12=0.05451613664627075 · same_winery_in_top=1 · same_color_in_top=0 · same_category_in_top=0

| # | relation | file | name | winery | color | grape | category |
|--:|----------|------|------|--------|-------|-------|----------|
| 1 | `other` | `golubitskoe-estate-merlo-krasnoe-suhoe-135.webp` | Мерло | Golubitskoe Estate | Темно-рубиновый | Мерло | Красное |
| 2 | `other` | `golubitskoe-estate-kaberne-sovinon-krasnoe-suhoe-137.webp` | Каберне Совиньон | Golubitskoe Estate | Темно-рубиновый с гранатовым ободком | Каберне Совиньон | Красное |
| 3 | `other` | `golubitskoe-estate-sovinon-blan-beloe-suhoe-11.webp` | Совиньон Блан | Golubitskoe Estate | Светло-соломенный | Совиньон Блан | Белое |
| 4 | `same_winery` | `golubitskoe-estate-chardonnay.webp` | Golubitskoe Estate Chardonnay | Поместье Голубицкое | Светло-соломенный | Шардоне | Белое |
| 5 | `other` | `golubitskoe-estate-risling.webp` | Golubitskoe Estate Рислинг | Golubitskoe Estate | Золотисто-соломенный | Рислинг | Белое |

---

## Training signals (heuristic)

- High `same_winery` in miss tops → need stronger **within-winery** separation (margin / hard same-winery negatives).
- High `other` + same color/category → **lookalike packaging / line twins** across producers; near-cluster or hard-FAR mining.
- Color flips (e.g. red GT → white/sparkling tops) → preprocess / label noise / weak visual cue; check query crop quality before changing loss.
