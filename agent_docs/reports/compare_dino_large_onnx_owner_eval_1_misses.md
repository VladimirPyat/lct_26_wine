# DINOv2-large P1 ONNX — miss@5 cards (owner_eval set1 / Dev-A)

**Model tag:** `dinov2_large_wine_phase1`  
**Scored:** 27  ·  **Hit@5:** 21  ·  **Miss@5:** 6  ·  **R@5:** 0.778

Slug meta from `data/owner_database/wines_integrated_updated.csv` (name · winery · color · grape · category).

---

## Aggregates on miss queries (top-k slots)

| relation | slots |
|----------|------:|
| `other` | 21 |
| `same_winery` | 9 |

### Frequent intruders (appear in miss top-k, not GT)

| n | file | winery (from CSV) |
|--:|------|-------------------|
| 2 | `relikta-relikta-pervenets-muskat-pervenets-magaracha-beloe-polusladkoe-125.webp` | Реликта |
| 2 | `cock-test-belle-kyuve-2-blan-de-nuar-pino-mene-beloe-ekstra-bryut-12.webp` | Cock t'est belle |
| 1 | `lesnaya-proseka.webp` | Кубань-Вино |
| 1 | `vinodelnya-batrak-contadina-merlo-krasnoe-suhoe-14.webp` | Винодельня Батрак |
| 1 | `derbent-vino-graf-vorontsov-bryut-beloe-sovinon-blan-105-125.webp` | Дербент Вино |
| 1 | `villa-di-alma-pti-verdo-krasnoe-suhoe-125.webp` | Villa di Alma |
| 1 | `dacha-serdyuka-sibirkovyy-oranzh-beloe-suhoe-135.webp` | Дача Сердюка |
| 1 | `derbent-vino-endemy-sovinon-beloe-bryut-105-125.webp` | Дербент Вино |
| 1 | `massandra-muskatel-chernyy-krasnye-sorta-vinograda-krasnoe-sladkoe-16.webp` | Массандра |
| 1 | `massandra-muskat-belyy-yuzhnoberezhnyy-beloe-sladkoe-16.webp` | Массандра |
| 1 | `massandra-kagor-gurzuf-saperavi-krasnoe-sladkoe-16.webp` | Массандра |
| 1 | `massandra-portveyn-krasnyy-livadiya-kaberne-sovinon-krasnoe-sladkoe-185.webp` | Массандра |
| 1 | `massandra-bastardo-bastardo-magarachskiy-krasnoe-sladkoe-16.webp` | Массандра |
| 1 | `belbek-sovinon-blan-beloe-suhoe-12.webp` | Бельбек |
| 1 | `belbek-pino-nuar-krasnoe-suhoe-133.webp` | Бельбек |
| 1 | `belbek-pino-nuar-rezerv-krasnoe-suhoe-135.webp` | Бельбек |
| 1 | `belbek-belbek-pino-nuar-krasnoe-suhoe-13.webp` | Бельбек |
| 1 | `agora-saperavi.webp` | AGORA WINERY |
| 1 | `riesling.webp` | WINEMAFIA |
| 1 | `orange.webp` | WINEMAFIA |
| 1 | `vermentino-viognier-2022.webp` | Vibes |
| 1 | `appassimento.webp` | WINEMAFIA |
| 1 | `vinodelnya-raevskoe-renessans-blaufrankish-krasnoe-suhoe-128.webp` | Раевское |
| 1 | `vinodelnya-vedernikov-gubernatorskoe-risling-beloe-suhoe-12.webp` | Ведерниковъ |
| 1 | `fanagoriya-primum-alveus-blanc-de-noirs-meunier-ekstra-bryut-2019-mene-beloe-11-13.webp` | Фанагория |

### Intruder wineries

| n | winery |
|--:|--------|
| 5 | Массандра |
| 4 | Бельбек |
| 3 | Дербент Вино |
| 3 | WINEMAFIA |
| 2 | Кубань-Вино |
| 2 | Реликта |
| 2 | Cock t'est belle |
| 2 | Фанагория |
| 1 | Винодельня Батрак |
| 1 | Villa di Alma |
| 1 | Дача Сердюка |
| 1 | AGORA WINERY |
| 1 | Vibes |
| 1 | Раевское |
| 1 | Ведерниковъ |

### Color GT → top candidate

| n | pattern |
|--:|---------|
| 2 | Розовый, насыщенный → Тёмно-рубиновый |
| 1 | Интенсивный рубиново-красный с фиолетовым оттенком. → Светло-золотистый |
| 1 | Интенсивный рубиново-красный с фиолетовым оттенком. → Красновато-багряный |
| 1 | Интенсивный рубиново-красный с фиолетовым оттенком. → Светло-соломенный |
| 1 | Интенсивный рубиново-красный с фиолетовым оттенком. → Бледно-соломенный |
| 1 | Интенсивный рубиново-красный с фиолетовым оттенком. → Серебристо-белый, практически прозрачный |
| 1 | рубиновый средней интенсивности → Глубокий рубиновый цвет с чернильным оттенком. |
| 1 | рубиновый средней интенсивности → Светло-соломенный |
| 1 | рубиновый средней интенсивности → Бледно-соломенный |
| 1 | рубиновый средней интенсивности → Янтарно-золотой |
| 1 | рубиновый средней интенсивности → Светло-соломенный с зеленоватым оттенком |
| 1 | Розовый, насыщенный → Насыщенный золотистый цвет с красивыми бликами тёмного янтаря. |
| 1 | Розовый, насыщенный → Тёмно-рубиновый с коричневатым оттенком |
| 1 | Розовый, насыщенный → Тёмно-рубиновый с фиолетовым оттенком |
| 1 | Светло-соломенный с зеленоватым оттенком → Зеленовато-соломенный |
| 1 | Светло-соломенный с зеленоватым оттенком → Сдержанный рубиновый |
| 1 | Светло-соломенный с зеленоватым оттенком → Красивый темно-рубиновый |
| 1 | Светло-соломенный с зеленоватым оттенком → Светло-рубиновый, прозрачный |
| 1 | Светло-соломенный с зеленоватым оттенком → Темно-рубиновый |
| 1 | Светло-золотистый → Соломенный, с зеленоватым оттенком |

### Winery GT → top candidate

| n | pattern |
|--:|---------|
| 5 | Массандра → Массандра |
| 4 | Бельбек → Бельбек |
| 3 | Alma Valley → WINEMAFIA |
| 2 | Alma Valley → Фанагория |
| 1 | Криница → Кубань-Вино |
| 1 | Криница → Винодельня Батрак |
| 1 | Криница → Реликта |
| 1 | Криница → Cock t'est belle |
| 1 | Криница → Дербент Вино |
| 1 | Винодельня Бюрнье → Villa di Alma |
| 1 | Винодельня Бюрнье → Реликта |
| 1 | Винодельня Бюрнье → Cock t'est belle |
| 1 | Винодельня Бюрнье → Дача Сердюка |
| 1 | Винодельня Бюрнье → Дербент Вино |
| 1 | Бельбек → AGORA WINERY |
| 1 | Alma Valley → Vibes |
| 1 | Alma Valley → Раевское |
| 1 | Alma Valley → Ведерниковъ |
| 1 | Alma Valley → Кубань-Вино |
| 1 | Alma Valley → Дербент Вино |

---

## Miss cards (rank > 5)

### `ef930b69.jpg` — rank **7**

**GT:** `vinodelnya-krinitsa-arena-sira-krasnoe-suhoe-13.webp`  
Арена · Криница · Интенсивный рубиново-красный с фиолетовым оттенком. · Сира · Красное

gap12=0.028681933879852295 · same_winery_in_top=0 · same_color_in_top=0 · same_category_in_top=1

| # | relation | file | name | winery | color | grape | category |
|--:|----------|------|------|--------|-------|-------|----------|
| 1 | `other` | `lesnaya-proseka.webp` | Лесная просека | Кубань-Вино | Светло-золотистый | Алиготе, Пино Блан, Шардоне | Белое |
| 2 | `other` | `vinodelnya-batrak-contadina-merlo-krasnoe-suhoe-14.webp` | Contadina | Винодельня Батрак | Красновато-багряный | Мерло | Красное |
| 3 | `other` | `relikta-relikta-pervenets-muskat-pervenets-magaracha-beloe-polusladkoe-125.webp` | Реликта Первенец Мускат | Реликта | Светло-соломенный | Мускат Белый, Первенец Магарача | Белое |
| 4 | `other` | `cock-test-belle-kyuve-2-blan-de-nuar-pino-mene-beloe-ekstra-bryut-12.webp` | Кюве №2 Блан Де Нуар | Cock t'est belle | Бледно-соломенный | Пино Менье | Белое |
| 5 | `other` | `derbent-vino-graf-vorontsov-bryut-beloe-sovinon-blan-105-125.webp` | Граф Воронцов. Брют белое | Дербент Вино | Серебристо-белый, практически прозрачный | Первенец Магарача, Ркацители, Совиньон Блан, Шардоне | Белое |

### `8a8ad5d7.jpeg` — rank **8**

**GT:** `vinodelnya-byurne-lyublyu-krasnoe-kaberne-fran-suhoe-135.webp`  
БЮРНЬЕ.ЛЮБЛЮ сухое красное · Винодельня Бюрнье · рубиновый средней интенсивности · Каберне Фран, Мерло, Сира · Красное

gap12=0.10234665870666504 · same_winery_in_top=0 · same_color_in_top=0 · same_category_in_top=1

| # | relation | file | name | winery | color | grape | category |
|--:|----------|------|------|--------|-------|-------|----------|
| 1 | `other` | `villa-di-alma-pti-verdo-krasnoe-suhoe-125.webp` | Пти Вердо | Villa di Alma | Глубокий рубиновый цвет с чернильным оттенком. | Пти Вердо | Красное |
| 2 | `other` | `relikta-relikta-pervenets-muskat-pervenets-magaracha-beloe-polusladkoe-125.webp` | Реликта Первенец Мускат | Реликта | Светло-соломенный | Мускат Белый, Первенец Магарача | Белое |
| 3 | `other` | `cock-test-belle-kyuve-2-blan-de-nuar-pino-mene-beloe-ekstra-bryut-12.webp` | Кюве №2 Блан Де Нуар | Cock t'est belle | Бледно-соломенный | Пино Менье | Белое |
| 4 | `other` | `dacha-serdyuka-sibirkovyy-oranzh-beloe-suhoe-135.webp` | Сибирьковый Оранж | Дача Сердюка | Янтарно-золотой | Сибирьковый | Белое |
| 5 | `other` | `derbent-vino-endemy-sovinon-beloe-bryut-105-125.webp` | Эндемы Совиньон | Дербент Вино | Светло-соломенный с зеленоватым оттенком | Совиньон | Белое |

### `3c11e5b0.jpeg` — rank **11**

**GT:** `massandra-muskatel-rozovyy-belye-sorta-vinograda-rozovoe-sladkoe-16.webp`  
Мускатель розовый · Массандра · Розовый, насыщенный · Белые сорта винограда, Красные сорта винограда · Розовое

gap12=0.0038732290267944336 · same_winery_in_top=5 · same_color_in_top=0 · same_category_in_top=0

| # | relation | file | name | winery | color | grape | category |
|--:|----------|------|------|--------|-------|-------|----------|
| 1 | `same_winery` | `massandra-muskatel-chernyy-krasnye-sorta-vinograda-krasnoe-sladkoe-16.webp` | Мускатель черный | Массандра | Тёмно-рубиновый | Красные сорта винограда | Красное |
| 2 | `same_winery` | `massandra-muskat-belyy-yuzhnoberezhnyy-beloe-sladkoe-16.webp` | Мускат Белый Южнобережный | Массандра | Насыщенный золотистый цвет с красивыми бликами тёмного янтаря. | Мускат Белый | Белое |
| 3 | `same_winery` | `massandra-kagor-gurzuf-saperavi-krasnoe-sladkoe-16.webp` | Кагор Гурзуф | Массандра | Тёмно-рубиновый | Бастардо Магарачский, Каберне Совиньон, Саперави | Красное |
| 4 | `same_winery` | `massandra-portveyn-krasnyy-livadiya-kaberne-sovinon-krasnoe-sladkoe-185.webp` | Портвейн красный Ливадия | Массандра | Тёмно-рубиновый с коричневатым оттенком | Каберне Совиньон | Красное |
| 5 | `same_winery` | `massandra-bastardo-bastardo-magarachskiy-krasnoe-sladkoe-16.webp` | Бастардо | Массандра | Тёмно-рубиновый с фиолетовым оттенком | Бастардо Магарачский | Красное |

### `7bf0507b.jpg` — rank **19**

**GT:** `belbek-belbek-muskat-beloe-suhoe-128.webp`  
Бельбек Мускат · Бельбек · Светло-соломенный с зеленоватым оттенком · Мускат · Белое

gap12=0.016860365867614746 · same_winery_in_top=4 · same_color_in_top=0 · same_category_in_top=1

| # | relation | file | name | winery | color | grape | category |
|--:|----------|------|------|--------|-------|-------|----------|
| 1 | `same_winery` | `belbek-sovinon-blan-beloe-suhoe-12.webp` | Совиньон Блан | Бельбек | Зеленовато-соломенный | Совиньон Блан | Белое |
| 2 | `same_winery` | `belbek-pino-nuar-krasnoe-suhoe-133.webp` | Пино Нуар | Бельбек | Сдержанный рубиновый | Пино Нуар | Красное |
| 3 | `same_winery` | `belbek-pino-nuar-rezerv-krasnoe-suhoe-135.webp` | Пино Нуар Резерв | Бельбек | Красивый темно-рубиновый | Пино Нуар | Красное |
| 4 | `same_winery` | `belbek-belbek-pino-nuar-krasnoe-suhoe-13.webp` | Бельбек Пино Нуар | Бельбек | Светло-рубиновый, прозрачный | Пино Нуар | Красное |
| 5 | `other` | `agora-saperavi.webp` | AGORA Саперави | AGORA WINERY | Темно-рубиновый | Саперави | Красное |

### `bd78e0f6.jpg` — rank **34**

**GT:** `alma-valley-graviti-pino-blan-beloe-suhoe-135.webp`  
Гравити · Alma Valley · Светло-золотистый · Пино Блан, Пино Гри, Рислинг · Белое

gap12=0.12044847011566162 · same_winery_in_top=0 · same_color_in_top=0 · same_category_in_top=3

| # | relation | file | name | winery | color | grape | category |
|--:|----------|------|------|--------|-------|-------|----------|
| 1 | `other` | `riesling.webp` | Riesling, 2024 | WINEMAFIA | Соломенный, с зеленоватым оттенком | Рислинг | Белое |
| 2 | `other` | `orange.webp` | Orange, 2023 | WINEMAFIA | Сухой насыщенной соломы | Рислинг | Белое |
| 3 | `other` | `vermentino-viognier-2022.webp` | Vermentino-Viognier 2022 | Vibes | Светло-соломенный | Верментино | Белое |
| 4 | `other` | `appassimento.webp` | Appassimento | WINEMAFIA | Плотный рубиново-красный с фиолетовыми отблесками | Каберне Совиньон | Красное |
| 5 | `other` | `vinodelnya-raevskoe-renessans-blaufrankish-krasnoe-suhoe-128.webp` | Ренессанс Блауфранкиш | Раевское | Чистый прозрачный рубиновый цвет с вишнево-пурпурными оттенками. | Блауфранкиш | Красное |

### `2039dd8a.jpg` — rank **100**

**GT:** `alma-valley-alma-graviti-pino-nuar-merlo-kaberne-sovinon-krasnoe-suhoe-14.webp`  
Альма Гравити. Пино Нуар - Мерло - Каберне Совиньон · Alma Valley · Рубиновый цвет с пурпурно-малиновыми оттенками и ровным блеском. · Пино Нуар · Красное

gap12=0.007922887802124023 · same_winery_in_top=0 · same_color_in_top=0 · same_category_in_top=2

| # | relation | file | name | winery | color | grape | category |
|--:|----------|------|------|--------|-------|-------|----------|
| 1 | `other` | `vinodelnya-vedernikov-gubernatorskoe-risling-beloe-suhoe-12.webp` | Губернаторское. Рислинг | Ведерниковъ | Соломенно-золотистый | Рислинг | Белое |
| 2 | `other` | `fanagoriya-primum-alveus-blanc-de-noirs-meunier-ekstra-bryut-2019-mene-beloe-11-13.webp` | Primum Alveus. Blanc de Noirs. Meunier. Экстра брют 2019 | Фанагория | Соломенный | Менье | Белое |
| 3 | `other` | `kuban-vino-aristov-anima-pino-nero-sandzhoveze-pino-nuar-krasnoe-suhoe-125.webp` | Аристов Анима Пино Неро Санджовезе | Кубань-Вино | Цвет вина варьируется от насыщенного до темного рубинового. | Пино Нуар, Санджовезе | Красное |
| 4 | `other` | `derbent-vino-di-kaspiko-merlo-krasnoe-polusladkoe-11.webp` | Ди Каспико | Дербент Вино | Глубокий алый | Мерло | Красное |
| 5 | `other` | `fanagoriya-primum-alveus-blanc-de-blancs-2017-shardone-igristoe-bryut-beloe-12.webp` | Primum Alveus Blanc de Blancs 2017 | Фанагория | Светло-золотистый | Шардоне | Белое |

---

## Training signals (heuristic)

- High `same_winery` in miss tops → need stronger **within-winery** separation (margin / hard same-winery negatives).
- High `other` + same color/category → **lookalike packaging / line twins** across producers; near-cluster or hard-FAR mining.
- Color flips (e.g. red GT → white/sparkling tops) → preprocess / label noise / weak visual cue; check query crop quality before changing loss.
