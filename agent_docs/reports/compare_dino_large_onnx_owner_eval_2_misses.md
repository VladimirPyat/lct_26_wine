# DINOv2-large P1 ONNX — miss@5 cards (owner_eval set2 / Dev-B)

**Model tag:** `dinov2_large_wine_phase1`  
**Scored:** 24  ·  **Hit@5:** 18  ·  **Miss@5:** 6  ·  **R@5:** 0.750

Slug meta from `data/owner_database/wines_integrated_updated.csv` (name · winery · color · grape · category).

---

## Aggregates on miss queries (top-k slots)

| relation | slots |
|----------|------:|
| `other` | 18 |
| `same_winery` | 12 |

### Frequent intruders (appear in miss top-k, not GT)

| n | file | winery (from CSV) |
|--:|------|-------------------|
| 2 | `pomeste-golubitskoe-kaberne-sovinon-rezerv-krasnoe-suhoe-143.webp` | Golubitskoe Estate |
| 2 | `pomeste-golubitskoe-shardone-rezerv-beloe-suhoe-132.webp` | Golubitskoe Estate |
| 1 | `golubitskoe-estate-merlo-krasnoe-suhoe-135.webp` | Golubitskoe Estate |
| 1 | `golubitskoe-estate-risling.webp` | Golubitskoe Estate |
| 1 | `golubitskoe-estate-kaberne-sovinon-krasnoe-suhoe-137.webp` | Golubitskoe Estate |
| 1 | `golubitskoe-estate-sovinon-blan-beloe-suhoe-11.webp` | Golubitskoe Estate |
| 1 | `golubitskoe-estate-risling-beloe-suhoe-125.webp` | Golubitskoe Estate |
| 1 | `perovskih_polusladkoe_krasnoe.webp` | Усадьба Перовских |
| 1 | `zolotoe-pole-legend-of-crimea-malbec-malbek-krasnoe-suhoe-125.webp` | Золотое Поле |
| 1 | `esse-kaberne-otbornoe-kaberne-sovinon-krasnoe-suhoe-12.webp` | ESSE |
| 1 | `vinodelnya-uzunov-roze-ekstra-bryut-kaberne-sovinon-rozovoe-127.webp` | Винодельня Узунов |
| 1 | `esse-merlo-otbornoe-krasnoe-suhoe-13.webp` | ESSE |
| 1 | `golubitskoe-estate-kaberne-sovinon-noble-selection-krasnoe-suhoe-133.webp` | Golubitskoe Estate |
| 1 | `vinodelnya-batrak-perfekt-klassik-merlo-krasnoe-suhoe-135.webp` | Винодельня Батрак |
| 1 | `golubitskoe-estate-noble-selection-red-blend-kaberne-sovinon-krasnoe-suhoe-136.webp` | Golubitskoe Estate |
| 1 | `cock-test-belle-kyuve-2-blan-de-nuar-pino-mene-beloe-ekstra-bryut-12.webp` | Cock t'est belle |
| 1 | `relikta-relikta-pervenets-muskat-pervenets-magaracha-beloe-polusladkoe-125.webp` | Реликта |
| 1 | `usadba-mezyb-usadba-mezyb-merlo-krasnoe-suhoe-15.webp` | Усадьба Мезыбь |
| 1 | `sober-bash-trezvaya-golova-tsimlyanskiygolubok-tsimlyanskiy-chernyy-krasnoe-suhoe-135.webp` | Собер Баш |
| 1 | `sober-bash-trezvaya-golova-kaberne-fran-krasnostop-krasnoe-suhoe-13.webp` | Собер Баш |
| 1 | `sober-bash-grani-plechistik-krasnoe-suhoe-12.webp` | Собер Баш |
| 1 | `belbek-merlo-krasnoe-suhoe-13.webp` | Бельбек |
| 1 | `belbek-pino-mene-krasnoe-suhoe-128.webp` | Бельбек |
| 1 | `vino-suhoe-beloe-endemy-shardone.webp` | Дербент Вино |
| 1 | `derbent-vino-endemy-pino-nuar-rozovoe-bryut-105-125.webp` | Дербент Вино |

### Intruder wineries

| n | winery |
|--:|--------|
| 11 | Golubitskoe Estate |
| 5 | Дербент Вино |
| 3 | Собер Баш |
| 2 | ESSE |
| 2 | Бельбек |
| 1 | Усадьба Перовских |
| 1 | Золотое Поле |
| 1 | Винодельня Узунов |
| 1 | Винодельня Батрак |
| 1 | Cock t'est belle |
| 1 | Реликта |
| 1 | Усадьба Мезыбь |

### Color GT → top candidate

| n | pattern |
|--:|---------|
| 2 | Рубиновый с легким пурпурным оттенком → Светло-соломенный |
| 1 | Светло-розовое → Темно-рубиновый |
| 1 | Светло-розовое → Золотисто-соломенный |
| 1 | Светло-розовое → Темно-рубиновый с гранатовым ободком |
| 1 | Светло-розовое → Светло-соломенный |
| 1 | Светло-розовое → Соломенный с переливающимися зеленоватыми искрами. |
| 1 | Насыщенный рубиновый → Вино с глубоким гранатовым оттенком. |
| 1 | Насыщенный рубиновый → Яркий рубиновый с пурпурным оттенком |
| 1 | Насыщенный рубиновый → Насыщенный красный |
| 1 | Насыщенный рубиновый → Бледно-розовый |
| 1 | Насыщенный рубиновый → Ярко-рубиновый |
| 1 | Глубокий рубиново-красный → Глубокий рубиново-красный цвет с гранатовыми оттенками. |
| 1 | Глубокий рубиново-красный → Вино бледно-лимонного цвета с зеленоватыми бликами. |
| 1 | Глубокий рубиново-красный → Насыщенный рубиново-вишневый |
| 1 | Глубокий рубиново-красный → Пурпурный |
| 1 | Глубокий рубиново-красный → Красивый гранатово-красный |
| 1 | Ягодно-красный → Бледно-соломенный |
| 1 | Ягодно-красный → Светло-соломенный |
| 1 | Ягодно-красный → Тёмно-рубиновый |
| 1 | Ягодно-красный → Гранатовый |

### Winery GT → top candidate

| n | pattern |
|--:|---------|
| 6 | Golubitskoe Estate → Golubitskoe Estate |
| 5 | Поместье Голубицкое → Golubitskoe Estate |
| 5 | Дербент Вино → Дербент Вино |
| 2 | Золотое Поле → ESSE |
| 2 | Дербент Вино → Собер Баш |
| 2 | Golubitskoe Estate → Бельбек |
| 1 | Золотое Поле → Усадьба Перовских |
| 1 | Золотое Поле → Золотое Поле |
| 1 | Золотое Поле → Винодельня Узунов |
| 1 | Golubitskoe Estate → Винодельня Батрак |
| 1 | Дербент Вино → Cock t'est belle |
| 1 | Дербент Вино → Реликта |
| 1 | Дербент Вино → Усадьба Мезыбь |
| 1 | Golubitskoe Estate → Собер Баш |

## GT missing from gallery

- `a0c040fc.jpg` → `skalistyy-bereg-veter-v-travah-kaberne-fran-krasnoe-suhoe-13.webp`  
  Ветер в травах · Скалистый берег · Светло-вишневый · Каберне Совиньон, Каберне Фран, Мерло · Красное

---

## Miss cards (rank > 5)

### `9b891f99.jpg` — rank **7**

**GT:** `golubitskoe-rose.webp`  
Golubitskoe Rose · Поместье Голубицкое · Светло-розовое · Каберне Совиньон, Мерло, Пино Гриджио, Пино Нуар · Розовое

gap12=0.02214375138282776 · same_winery_in_top=0 · same_color_in_top=0 · same_category_in_top=0

| # | relation | file | name | winery | color | grape | category |
|--:|----------|------|------|--------|-------|-------|----------|
| 1 | `other` | `golubitskoe-estate-merlo-krasnoe-suhoe-135.webp` | Мерло | Golubitskoe Estate | Темно-рубиновый | Мерло | Красное |
| 2 | `other` | `golubitskoe-estate-risling.webp` | Golubitskoe Estate Рислинг | Golubitskoe Estate | Золотисто-соломенный | Рислинг | Белое |
| 3 | `other` | `golubitskoe-estate-kaberne-sovinon-krasnoe-suhoe-137.webp` | Каберне Совиньон | Golubitskoe Estate | Темно-рубиновый с гранатовым ободком | Каберне Совиньон | Красное |
| 4 | `other` | `golubitskoe-estate-sovinon-blan-beloe-suhoe-11.webp` | Совиньон Блан | Golubitskoe Estate | Светло-соломенный | Совиньон Блан | Белое |
| 5 | `other` | `golubitskoe-estate-risling-beloe-suhoe-125.webp` | Рислинг | Golubitskoe Estate | Соломенный с переливающимися зеленоватыми искрами. | Рислинг | Белое |

### `1978bd14.jpg` — rank **8**

**GT:** `zolotoe-pole-legend-of-crimea-cabernet-sauvignon-kaberne-sovinon-krasnoe-suhoe-125.webp`  
Legend of Crimea "Cabernet Sauvignon" · Золотое Поле · Насыщенный рубиновый · Каберне Совиньон · Красное

gap12=0.03990045189857483 · same_winery_in_top=1 · same_color_in_top=0 · same_category_in_top=4

| # | relation | file | name | winery | color | grape | category |
|--:|----------|------|------|--------|-------|-------|----------|
| 1 | `other` | `perovskih_polusladkoe_krasnoe.webp` | Полусладкое Красное | Усадьба Перовских | Вино с глубоким гранатовым оттенком. | Каберне Совиньон, Мерло, Пино Нуар | Красное |
| 2 | `same_winery` | `zolotoe-pole-legend-of-crimea-malbec-malbek-krasnoe-suhoe-125.webp` | Legend of Crimea "Malbec" | Золотое Поле | Яркий рубиновый с пурпурным оттенком | Мальбек | Красное |
| 3 | `other` | `esse-kaberne-otbornoe-kaberne-sovinon-krasnoe-suhoe-12.webp` | Каберне Отборное | ESSE | Насыщенный красный | Каберне Совиньон | Красное |
| 4 | `other` | `vinodelnya-uzunov-roze-ekstra-bryut-kaberne-sovinon-rozovoe-127.webp` | Розе экстра брют | Винодельня Узунов | Бледно-розовый | Каберне Совиньон, Каберне Фран | Розовое |
| 5 | `other` | `esse-merlo-otbornoe-krasnoe-suhoe-13.webp` | Мерло Отборное | ESSE | Ярко-рубиновый | Мерло | Красное |

### `4ce9195c.jpg` — rank **10**

**GT:** `golubitskoe-estate-pino-nuar-rezerv-krasnoe-suhoe-132.webp`  
Пино Нуар Резерв · Golubitskoe Estate · Глубокий рубиново-красный · Пино Нуар · Красное

gap12=0.057787150144577026 · same_winery_in_top=4 · same_color_in_top=0 · same_category_in_top=4

| # | relation | file | name | winery | color | grape | category |
|--:|----------|------|------|--------|-------|-------|----------|
| 1 | `same_winery` | `pomeste-golubitskoe-kaberne-sovinon-rezerv-krasnoe-suhoe-143.webp` | Каберне Совиньон Резерв | Golubitskoe Estate | Глубокий рубиново-красный цвет с гранатовыми оттенками. | Каберне Совиньон | Красное |
| 2 | `same_winery` | `pomeste-golubitskoe-shardone-rezerv-beloe-suhoe-132.webp` | Шардоне Резерв | Golubitskoe Estate | Вино бледно-лимонного цвета с зеленоватыми бликами. | Шардоне | Белое |
| 3 | `same_winery` | `golubitskoe-estate-kaberne-sovinon-noble-selection-krasnoe-suhoe-133.webp` | Каберне Совиньон Noble Selection | Golubitskoe Estate | Насыщенный рубиново-вишневый | Каберне Совиньон | Красное |
| 4 | `other` | `vinodelnya-batrak-perfekt-klassik-merlo-krasnoe-suhoe-135.webp` | Perfekt Klassik Мерло | Винодельня Батрак | Пурпурный | Мерло | Красное |
| 5 | `same_winery` | `golubitskoe-estate-noble-selection-red-blend-kaberne-sovinon-krasnoe-suhoe-136.webp` | Noble Selection Red Blend | Golubitskoe Estate | Красивый гранатово-красный | Каберне Совиньон | Красное |

### `1f973b82.jpg` — rank **44**

**GT:** `vino-suhoe-krasnoe-endemy-saperavi.webp`  
Эндемы Саперави · Дербент Вино · Ягодно-красный · Саперави · Красное

gap12=0.013064861297607422 · same_winery_in_top=0 · same_color_in_top=0 · same_category_in_top=3

| # | relation | file | name | winery | color | grape | category |
|--:|----------|------|------|--------|-------|-------|----------|
| 1 | `other` | `cock-test-belle-kyuve-2-blan-de-nuar-pino-mene-beloe-ekstra-bryut-12.webp` | Кюве №2 Блан Де Нуар | Cock t'est belle | Бледно-соломенный | Пино Менье | Белое |
| 2 | `other` | `relikta-relikta-pervenets-muskat-pervenets-magaracha-beloe-polusladkoe-125.webp` | Реликта Первенец Мускат | Реликта | Светло-соломенный | Мускат Белый, Первенец Магарача | Белое |
| 3 | `other` | `usadba-mezyb-usadba-mezyb-merlo-krasnoe-suhoe-15.webp` | Усадьба Мезыбь. Мерло | Усадьба Мезыбь | Тёмно-рубиновый | Мерло | Красное |
| 4 | `other` | `sober-bash-trezvaya-golova-tsimlyanskiygolubok-tsimlyanskiy-chernyy-krasnoe-suhoe-135.webp` | Трезвая голова. Цимлянский+Голубок | Собер Баш | Гранатовый | Голубок, Цимлянский черный | Красное |
| 5 | `other` | `sober-bash-trezvaya-golova-kaberne-fran-krasnostop-krasnoe-suhoe-13.webp` | Трезвая голова. Каберне Фран + Красностоп | Собер Баш | Тёмно-гранатовый | Каберне Фран, Красностоп Золотовский | Красное |

### `54aa8496.jpg` — rank **58**

**GT:** `golubitskoe-estate-merlo-rezerv-krasnoe-suhoe-135.webp`  
Мерло Резерв · Golubitskoe Estate · Глубокий вишнево-рубиновый · Мерло · Красное

gap12=0.001735389232635498 · same_winery_in_top=2 · same_color_in_top=0 · same_category_in_top=4

| # | relation | file | name | winery | color | grape | category |
|--:|----------|------|------|--------|-------|-------|----------|
| 1 | `other` | `sober-bash-grani-plechistik-krasnoe-suhoe-12.webp` | Грани. Плечистик | Собер Баш | Гранатовый | Плечистик | Красное |
| 2 | `same_winery` | `pomeste-golubitskoe-kaberne-sovinon-rezerv-krasnoe-suhoe-143.webp` | Каберне Совиньон Резерв | Golubitskoe Estate | Глубокий рубиново-красный цвет с гранатовыми оттенками. | Каберне Совиньон | Красное |
| 3 | `same_winery` | `pomeste-golubitskoe-shardone-rezerv-beloe-suhoe-132.webp` | Шардоне Резерв | Golubitskoe Estate | Вино бледно-лимонного цвета с зеленоватыми бликами. | Шардоне | Белое |
| 4 | `other` | `belbek-merlo-krasnoe-suhoe-13.webp` | Мерло | Бельбек | Темно-рубиновый | Мерло | Красное |
| 5 | `other` | `belbek-pino-mene-krasnoe-suhoe-128.webp` | Пино Менье | Бельбек | Гранатово-красный | Пино Менье | Красное |

### `750a209e.jpg` — rank **150**

**GT:** `derbent-vino-endemy-kaberne-sovinon-krasnoe-suhoe-13.webp`  
Эндемы Каберне Совиньон · Дербент Вино · Рубиновый с легким пурпурным оттенком · Каберне Совиньон · Красное

gap12=0.0004469156265258789 · same_winery_in_top=5 · same_color_in_top=0 · same_category_in_top=0

| # | relation | file | name | winery | color | grape | category |
|--:|----------|------|------|--------|-------|-------|----------|
| 1 | `same_winery` | `vino-suhoe-beloe-endemy-shardone.webp` | Эндемы Шардоне | Дербент Вино | Светло-соломенный | Шардоне | Белое |
| 2 | `same_winery` | `derbent-vino-endemy-pino-nuar-rozovoe-bryut-105-125.webp` | Эндемы Пино Нуар | Дербент Вино | Нежно-розовый | Пино Нуар | Розовое |
| 3 | `same_winery` | `derbent-vino-endemy-sovinon-beloe-bryut-105-125.webp` | Эндемы Совиньон | Дербент Вино | Светло-соломенный с зеленоватым оттенком | Совиньон | Белое |
| 4 | `same_winery` | `derbent-vino-endemy-shardone-beloe-bryut-105-125.webp` | Эндемы Шардоне | Дербент Вино | Соломенный | Шардоне | Белое |
| 5 | `same_winery` | `vino-suhoe-beloe-endemy-sovinon.webp` | Эндемы Совиньон | Дербент Вино | Светло-соломенный | Совиньон Блан | Белое |

---

## Training signals (heuristic)

- High `same_winery` in miss tops → need stronger **within-winery** separation (margin / hard same-winery negatives).
- High `other` + same color/category → **lookalike packaging / line twins** across producers; near-cluster or hard-FAR mining.
- Color flips (e.g. red GT → white/sparkling tops) → preprocess / label noise / weak visual cue; check query crop quality before changing loss.
