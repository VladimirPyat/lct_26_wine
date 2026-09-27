# DINOv2-large P1 ONNX + YOLO crop — miss@5 cards (owner_eval set2)

**Model tag:** `dinov2_large_wine_phase1`  
**Scored:** 24  ·  **Hit@5:** 22  ·  **Miss@5:** 2  ·  **R@5:** 0.917

Slug meta from `data/owner_database/wines_integrated_updated.csv` (name · winery · color · grape · category).

---

## Aggregates on miss queries (top-k slots)

| relation | slots |
|----------|------:|
| `other` | 5 |
| `same_winery` | 5 |

### Frequent intruders (appear in miss top-k, not GT)

| n | file | winery (from CSV) |
|--:|------|-------------------|
| 1 | `golubitskoe-estate-merlo-krasnoe-suhoe-135.webp` | Golubitskoe Estate |
| 1 | `golubitskoe-estate-kaberne-sovinon-krasnoe-suhoe-137.webp` | Golubitskoe Estate |
| 1 | `golubitskoe-estate-sovinon-blan-beloe-suhoe-11.webp` | Golubitskoe Estate |
| 1 | `golubitskoe-estate-chardonnay.webp` | Поместье Голубицкое |
| 1 | `golubitskoe-estate-risling.webp` | Golubitskoe Estate |
| 1 | `derbent-vino-endemy-pino-nuar-rozovoe-bryut-105-125.webp` | Дербент Вино |
| 1 | `vino-suhoe-rozovoe-endemy-kaberne-sovinon.webp` | Дербент Вино |
| 1 | `derbent-vino-endemy-sovinon-beloe-bryut-105-125.webp` | Дербент Вино |
| 1 | `derbent-vino-endemy-shardone-beloe-bryut-105-125.webp` | Дербент Вино |
| 1 | `usadba-mezyb-usadba-mezyb-merlo-krasnoe-suhoe-15.webp` | Усадьба Мезыбь |

### Intruder wineries

| n | winery |
|--:|--------|
| 4 | Golubitskoe Estate |
| 4 | Дербент Вино |
| 1 | Поместье Голубицкое |
| 1 | Усадьба Мезыбь |

### Color GT → top candidate

| n | pattern |
|--:|---------|
| 2 | Светло-розовое → Светло-соломенный |
| 1 | Светло-розовое → Темно-рубиновый |
| 1 | Светло-розовое → Темно-рубиновый с гранатовым ободком |
| 1 | Светло-розовое → Золотисто-соломенный |
| 1 | Рубиновый с легким пурпурным оттенком → Нежно-розовый |
| 1 | Рубиновый с легким пурпурным оттенком → Бледно розовый |
| 1 | Рубиновый с легким пурпурным оттенком → Светло-соломенный с зеленоватым оттенком |
| 1 | Рубиновый с легким пурпурным оттенком → Соломенный |
| 1 | Рубиновый с легким пурпурным оттенком → Тёмно-рубиновый |

### Winery GT → top candidate

| n | pattern |
|--:|---------|
| 4 | Поместье Голубицкое → Golubitskoe Estate |
| 4 | Дербент Вино → Дербент Вино |
| 1 | Поместье Голубицкое → Поместье Голубицкое |
| 1 | Дербент Вино → Усадьба Мезыбь |

## GT missing from gallery

- `a0c040fc.jpg` → `skalistyy-bereg-veter-v-travah-kaberne-fran-krasnoe-suhoe-13.webp`  
  Ветер в травах · Скалистый берег · Светло-вишневый · Каберне Совиньон, Каберне Фран, Мерло · Красное

---

## Miss cards (rank > 5)

### `9b891f99.jpg` — rank **6**

**GT:** `golubitskoe-rose.webp`  
Golubitskoe Rose · Поместье Голубицкое · Светло-розовое · Каберне Совиньон, Мерло, Пино Гриджио, Пино Нуар · Розовое

gap12=0.053746044635772705 · same_winery_in_top=1 · same_color_in_top=0 · same_category_in_top=0

| # | relation | file | name | winery | color | grape | category |
|--:|----------|------|------|--------|-------|-------|----------|
| 1 | `other` | `golubitskoe-estate-merlo-krasnoe-suhoe-135.webp` | Мерло | Golubitskoe Estate | Темно-рубиновый | Мерло | Красное |
| 2 | `other` | `golubitskoe-estate-kaberne-sovinon-krasnoe-suhoe-137.webp` | Каберне Совиньон | Golubitskoe Estate | Темно-рубиновый с гранатовым ободком | Каберне Совиньон | Красное |
| 3 | `other` | `golubitskoe-estate-sovinon-blan-beloe-suhoe-11.webp` | Совиньон Блан | Golubitskoe Estate | Светло-соломенный | Совиньон Блан | Белое |
| 4 | `same_winery` | `golubitskoe-estate-chardonnay.webp` | Golubitskoe Estate Chardonnay | Поместье Голубицкое | Светло-соломенный | Шардоне | Белое |
| 5 | `other` | `golubitskoe-estate-risling.webp` | Golubitskoe Estate Рислинг | Golubitskoe Estate | Золотисто-соломенный | Рислинг | Белое |

### `750a209e.jpg` — rank **8**

**GT:** `derbent-vino-endemy-kaberne-sovinon-krasnoe-suhoe-13.webp`  
Эндемы Каберне Совиньон · Дербент Вино · Рубиновый с легким пурпурным оттенком · Каберне Совиньон · Красное

gap12=0.09287980198860168 · same_winery_in_top=4 · same_color_in_top=0 · same_category_in_top=1

| # | relation | file | name | winery | color | grape | category |
|--:|----------|------|------|--------|-------|-------|----------|
| 1 | `same_winery` | `derbent-vino-endemy-pino-nuar-rozovoe-bryut-105-125.webp` | Эндемы Пино Нуар | Дербент Вино | Нежно-розовый | Пино Нуар | Розовое |
| 2 | `same_winery` | `vino-suhoe-rozovoe-endemy-kaberne-sovinon.webp` | Эндемы Каберне Совиньон розовое | Дербент Вино | Бледно розовый | Каберне Совиньон | Розовое |
| 3 | `same_winery` | `derbent-vino-endemy-sovinon-beloe-bryut-105-125.webp` | Эндемы Совиньон | Дербент Вино | Светло-соломенный с зеленоватым оттенком | Совиньон | Белое |
| 4 | `same_winery` | `derbent-vino-endemy-shardone-beloe-bryut-105-125.webp` | Эндемы Шардоне | Дербент Вино | Соломенный | Шардоне | Белое |
| 5 | `other` | `usadba-mezyb-usadba-mezyb-merlo-krasnoe-suhoe-15.webp` | Усадьба Мезыбь. Мерло | Усадьба Мезыбь | Тёмно-рубиновый | Мерло | Красное |

---

## Training signals (heuristic)

- High `same_winery` in miss tops → need stronger **within-winery** separation (margin / hard same-winery negatives).
- High `other` + same color/category → **lookalike packaging / line twins** across producers; near-cluster or hard-FAR mining.
- Color flips (e.g. red GT → white/sparkling tops) → preprocess / label noise / weak visual cue; check query crop quality before changing loss.
