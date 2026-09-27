# SigLIP2 P1 ep3 Dev-B — queries with GT not at rank 1

**Model tag:** `siglip2_p1_ep3_devB`  
**Scored:** 24  ·  **Hit@1:** 15  ·  **Miss@1:** 9  ·  **R@1:** 0.625

Slug meta from `data/owner_database/wines_integrated_updated.csv` (name · winery · color · grape · category).

---

## Aggregates on miss queries (top-k slots)

| relation | slots |
|----------|------:|
| `other` | 22 |
| `near` | 10 |
| `same_winery` | 8 |
| `GT` | 5 |

### Frequent intruders (appear in miss top-k, not GT)

| n | file | winery (from CSV) |
|--:|------|-------------------|
| 3 | `leto-kaberne-fran-rezerv-2021-suhoe-krasnoe.webp` | LETO |
| 1 | `abrau-dyurso-abrau-estates-amurskiy-potapenko-krasnoe-suhoe-105.webp` | Абрау-Дюрсо |
| 1 | `abrau-dyurso-abrau-estates-roze-kaberne-sovinon-rozovoe-suhoe-12.webp` | Абрау-Дюрсо |
| 1 | `abrau-dyurso-abrau-estates-kaberne-po-belomu-kaberne-sovinon-beloe-suhoe-105.webp` | Абрау-Дюрсо |
| 1 | `abrau-dyurso-abrau-estates-krasnoe-kaberne-sovinon-suhoe-13.webp` | Абрау-Дюрсо |
| 1 | `usadba-divnomorskoe-yuzhnyy-les-merlo-krasnoe-suhoe-137.webp` | Усадьба Дивноморское |
| 1 | `vinodelnya-byurne-krasnostop-krasnoe-suhoe-145.webp` | Винодельня Бюрнье |
| 1 | `vinodelnya-uzunov-nrav-krasnostop-zolotovskiy-krasnoe-suhoe-132.webp` | Винодельня Узунов |
| 1 | `perovskih_merlo.webp` | Усадьба Перовских |
| 1 | `chateau-de-talu-uroki-frantsuzskogo-sovinon-blan-beloe-suhoe-115.webp` | Chateau de Talu |
| 1 | `chateau-de-talu-uroki-frantsuzskogo-sira-krasnoe-suhoe-13.webp` | Chateau de Talu |
| 1 | `chateau-de-talu-uroki-frantsuzskogo-merlo-krasnoe-suhoe-147.webp` | Chateau de Talu |
| 1 | `chateau-de-talu-uroki-frantsuzskogo-shardone-beloe-suhoe-124.webp` | Chateau de Talu |
| 1 | `belbek-kaberne-fran-krasnoe-suhoe-134.webp` | Бельбек |
| 1 | `belbek-belbek-kaberne-fran-krasnoe-suhoe-13.webp` | Бельбек |
| 1 | `belbek-sovinon-blan-beloe-suhoe-12.webp` | Бельбек |
| 1 | `agora-saperavi.webp` | AGORA WINERY |
| 1 | `vinodelnya-vedernikov-vedernikov-gubernatorskoe-golubok-krasnoe-suhoe-115.webp` | Ведерниковъ |
| 1 | `vinodelnya-vedernikov-vedernikov-dolina-dona-beloe-suhoe-aligote-12.webp` | Ведерниковъ |
| 1 | `vinodelnya-vedernikov-sibirkovyy-beloe-suhoe-11.webp` | Ведерниковъ |
| 1 | `vinodelnya-vedernikov-krasnostop-zolotovskiy-krasnoe-suhoe-13.webp` | Ведерниковъ |
| 1 | `golubitskoe-estate-noble-selection-red-blend-kaberne-sovinon-krasnoe-suhoe-136.webp` | Golubitskoe Estate |
| 1 | `golubitskoe-estate-kaberne-sovinon-noble-selection-krasnoe-suhoe-133.webp` | Golubitskoe Estate |
| 1 | `pomeste-golubitskoe-kaberne-sovinon-rezerv-krasnoe-suhoe-143.webp` | Golubitskoe Estate |
| 1 | `golubitskoe-estate-kaberne-sovinon-rezerv-krasnoe-suhoe-125.webp` | Golubitskoe Estate |

### Intruder wineries

| n | winery |
|--:|--------|
| 6 | Ведерниковъ |
| 5 | Golubitskoe Estate |
| 4 | Абрау-Дюрсо |
| 4 | Chateau de Talu |
| 3 | Бельбек |
| 3 | LETO |
| 3 | Усадьба Мезыбь |
| 2 | Винодельня Бюрнье |
| 2 | Винодельня Узунов |
| 1 | Усадьба Дивноморское |
| 1 | Усадьба Перовских |
| 1 | AGORA WINERY |
| 1 | ЗМВ Коктебель |
| 1 | Агролайн |
| 1 | STN Winery |

### Color GT → top candidate

| n | pattern |
|--:|---------|
| 2 | Глубокий красно-рубиновый → Тёмно-рубиновый |
| 1 | Рубиновый → Рубиновый с пурпурным оттенком |
| 1 | Рубиновый → Нежно-розовый |
| 1 | Рубиновый → Соломенный с розовым оттенком |
| 1 | Рубиновый → Тёмно-гранатовый |
| 1 | Рубиновый → Вино яркого рубинового цвета с блеском. |
| 1 | Рубиновый → Насыщенный рубиновый |
| 1 | Рубиновый → Тёмно-рубиновый |
| 1 | Рубиновый → Цвет глубокий розовой с персиковым блеском. |
| 1 | Рубиновый, с бликами по ободку → Вино бледно-зеленоватого цвета. |
| 1 | Рубиновый, с бликами по ободку → Рубиновый |
| 1 | Рубиновый, с бликами по ободку → Рубиновый, с глянцевыми бликами |
| 1 | Рубиновый, с бликами по ободку → Золотистый, с прозрачными бликами по ободку |
| 1 | Темно-гранатовый → Темный красно-рубиновый |
| 1 | Темно-гранатовый → Рубиновый с гранатовым отливом |
| 1 | Темно-гранатовый → Зеленовато-соломенный |
| 1 | Темно-гранатовый → Темно-рубиновый |
| 1 | Рубиновый с гранатовым отливом → Рубиновый с гранатовым отливом |
| 1 | Рубиновый с гранатовым отливом → Светло-соломенный с зеленоватым оттенком |
| 1 | Рубиновый с гранатовым отливом → Светло-соломенный |

### Winery GT → top candidate

| n | pattern |
|--:|---------|
| 5 | Golubitskoe Estate → Golubitskoe Estate |
| 4 | Абрау-Дюрсо → Абрау-Дюрсо |
| 4 | Chateau de Talu → Chateau de Talu |
| 4 | Ведерниковъ → Ведерниковъ |
| 3 | AGORA WINERY → Бельбек |
| 3 | Golubitskoe Estate → Усадьба Мезыбь |
| 2 | Золотое Поле → Ведерниковъ |
| 2 | Золотое Поле → LETO |
| 1 | Alma Valley → Усадьба Дивноморское |
| 1 | Alma Valley → Винодельня Бюрнье |
| 1 | Alma Valley → Винодельня Узунов |
| 1 | Alma Valley → Усадьба Перовских |
| 1 | AGORA WINERY → AGORA WINERY |
| 1 | Golubitskoe Estate → ЗМВ Коктебель |
| 1 | Золотое Поле → Агролайн |
| 1 | Золотое Поле → STN Winery |
| 1 | Golubitskoe Estate → LETO |
| 1 | Золотое Поле → Скалистый берег |
| 1 | Золотое Поле → ЛОРИО -  семейная винодельня Логуновых |
| 1 | Золотое Поле → Винодельня Узунов |

---

## Miss cards (rank > 1)

### `0c5e3b2b.jpg` — rank **2**

**GT:** `abrau-dyurso-abrau-estates-dostoynyy-krasnoe-suhoe-135.webp`  
Abrau Estates. Достойный · Абрау-Дюрсо · Рубиновый · Достойный · Красное

gap12=-0.0337 · same_winery_in_top=5 · same_color_in_top=1 · same_category_in_top=3

| # | relation | file | name | winery | color | grape | category |
|--:|----------|------|------|--------|-------|-------|----------|
| 1 | `near` | `abrau-dyurso-abrau-estates-amurskiy-potapenko-krasnoe-suhoe-105.webp` | Abrau Estates Амурский Потапенко | Абрау-Дюрсо | Рубиновый с пурпурным оттенком | Амурский Потапенко | Красное |
| 2 | `GT` | `abrau-dyurso-abrau-estates-dostoynyy-krasnoe-suhoe-135.webp` | Abrau Estates. Достойный | Абрау-Дюрсо | Рубиновый | Достойный | Красное |
| 3 | `near` | `abrau-dyurso-abrau-estates-roze-kaberne-sovinon-rozovoe-suhoe-12.webp` | Abrau Estates. Розе | Абрау-Дюрсо | Нежно-розовый | Каберне Совиньон, Каберне Фран | Розовое |
| 4 | `near` | `abrau-dyurso-abrau-estates-kaberne-po-belomu-kaberne-sovinon-beloe-suhoe-105.webp` | Abrau Estates Каберне по-белому | Абрау-Дюрсо | Соломенный с розовым оттенком | Каберне Совиньон | Белое |
| 5 | `near` | `abrau-dyurso-abrau-estates-krasnoe-kaberne-sovinon-suhoe-13.webp` | Abrau Estates красное | Абрау-Дюрсо | Тёмно-гранатовый | Каберне Совиньон, Мерло | Красное |

### `4c01cccd.jpg` — rank **2**

**GT:** `alma-valley-pino-nuar-krasnoe-suhoe-13.webp`  
Пино Нуар · Alma Valley · Рубиновый · Пино Нуар · Красное

gap12=-0.0081 · same_winery_in_top=1 · same_color_in_top=1 · same_category_in_top=4

| # | relation | file | name | winery | color | grape | category |
|--:|----------|------|------|--------|-------|-------|----------|
| 1 | `other` | `usadba-divnomorskoe-yuzhnyy-les-merlo-krasnoe-suhoe-137.webp` | Южный Лес | Усадьба Дивноморское | Вино яркого рубинового цвета с блеском. | Мерло | Красное |
| 2 | `GT` | `alma-valley-pino-nuar-krasnoe-suhoe-13.webp` | Пино Нуар | Alma Valley | Рубиновый | Пино Нуар | Красное |
| 3 | `other` | `vinodelnya-byurne-krasnostop-krasnoe-suhoe-145.webp` | БЮРНЬЕ.КРАСНОСТОП сухое красное | Винодельня Бюрнье | Насыщенный рубиновый | Красностоп | Красное |
| 4 | `other` | `vinodelnya-uzunov-nrav-krasnostop-zolotovskiy-krasnoe-suhoe-132.webp` | Нрав | Винодельня Узунов | Тёмно-рубиновый | Каберне Совиньон, Красностоп Золотовский, Саперави | Красное |
| 5 | `other` | `perovskih_merlo.webp` | Мерло | Усадьба Перовских | Цвет глубокий розовой с персиковым блеском. | Мерло | Розовое |

### `6a687bbd.jpg` — rank **2**

**GT:** `chateau-de-talu-uroki-frantsuzskogo-kaberne-sovinon-krasnoe-suhoe-14.webp`  
Уроки французского. Каберне Совиньон · Chateau de Talu · Рубиновый, с бликами по ободку · Каберне Совиньон · Красное

gap12=-0.0163 · same_winery_in_top=5 · same_color_in_top=1 · same_category_in_top=3

| # | relation | file | name | winery | color | grape | category |
|--:|----------|------|------|--------|-------|-------|----------|
| 1 | `same_winery` | `chateau-de-talu-uroki-frantsuzskogo-sovinon-blan-beloe-suhoe-115.webp` | Уроки Французского.
 Совиньон Блан | Chateau de Talu | Вино бледно-зеленоватого цвета. | Совиньон Блан | Белое |
| 2 | `GT` | `chateau-de-talu-uroki-frantsuzskogo-kaberne-sovinon-krasnoe-suhoe-14.webp` | Уроки французского. Каберне Совиньон | Chateau de Talu | Рубиновый, с бликами по ободку | Каберне Совиньон | Красное |
| 3 | `same_winery` | `chateau-de-talu-uroki-frantsuzskogo-sira-krasnoe-suhoe-13.webp` | Уроки французского. Сира | Chateau de Talu | Рубиновый | Сира | Красное |
| 4 | `same_winery` | `chateau-de-talu-uroki-frantsuzskogo-merlo-krasnoe-suhoe-147.webp` | Уроки французского. Мерло | Chateau de Talu | Рубиновый, с глянцевыми бликами | Мерло | Красное |
| 5 | `same_winery` | `chateau-de-talu-uroki-frantsuzskogo-shardone-beloe-suhoe-124.webp` | Уроки французского Шардоне | Chateau de Talu | Золотистый, с прозрачными бликами по ободку | Шардоне | Белое |

### `c22cead9.jpg` — rank **2**

**GT:** `agora-bastardo.webp`  
AGORA Бастардо · AGORA WINERY · Темно-гранатовый · Бастардо · Красное

gap12=-0.0086 · same_winery_in_top=2 · same_color_in_top=1 · same_category_in_top=4

| # | relation | file | name | winery | color | grape | category |
|--:|----------|------|------|--------|-------|-------|----------|
| 1 | `other` | `belbek-kaberne-fran-krasnoe-suhoe-134.webp` | Каберне Фран | Бельбек | Темный красно-рубиновый | Каберне Фран | Красное |
| 2 | `GT` | `agora-bastardo.webp` | AGORA Бастардо | AGORA WINERY | Темно-гранатовый | Бастардо | Красное |
| 3 | `other` | `belbek-belbek-kaberne-fran-krasnoe-suhoe-13.webp` | Бельбек Каберне Фран | Бельбек | Рубиновый с гранатовым отливом | Каберне Фран | Красное |
| 4 | `other` | `belbek-sovinon-blan-beloe-suhoe-12.webp` | Совиньон Блан | Бельбек | Зеленовато-соломенный | Совиньон Блан | Белое |
| 5 | `same_winery` | `agora-saperavi.webp` | AGORA Саперави | AGORA WINERY | Темно-рубиновый | Саперави | Красное |

### `deab3b0b.jpg` — rank **2**

**GT:** `vinodelnya-vedernikov-vedernikov-dolina-dona-krasnoe-suhoe-kaberne-sovinon-125.webp`  
Ведерниковъ Долина Дона Красное Сухое · Ведерниковъ · Рубиновый с гранатовым отливом · Каберне Совиньон, Красностоп Золотовский, Цимлянский черный · Красное

gap12=-0.0049 · same_winery_in_top=5 · same_color_in_top=2 · same_category_in_top=3

| # | relation | file | name | winery | color | grape | category |
|--:|----------|------|------|--------|-------|-------|----------|
| 1 | `near` | `vinodelnya-vedernikov-vedernikov-gubernatorskoe-golubok-krasnoe-suhoe-115.webp` | Ведерниковъ Губернаторское «Голубок» | Ведерниковъ | Рубиновый с гранатовым отливом | Голубок, Каберне Совиньон, Цимлянский черный | Красное |
| 2 | `GT` | `vinodelnya-vedernikov-vedernikov-dolina-dona-krasnoe-suhoe-kaberne-sovinon-125.webp` | Ведерниковъ Долина Дона Красное Сухое | Ведерниковъ | Рубиновый с гранатовым отливом | Каберне Совиньон, Красностоп Золотовский, Цимлянский черный | Красное |
| 3 | `near` | `vinodelnya-vedernikov-vedernikov-dolina-dona-beloe-suhoe-aligote-12.webp` | Ведерниковъ Долина Дона Белое Сухое | Ведерниковъ | Светло-соломенный с зеленоватым оттенком | Алиготе, Рислинг, Ркацители, Сибирьковый | Белое |
| 4 | `near` | `vinodelnya-vedernikov-sibirkovyy-beloe-suhoe-11.webp` | Сибирьковый | Ведерниковъ | Светло-соломенный | Сибирьковый | Белое |
| 5 | `same_winery` | `vinodelnya-vedernikov-krasnostop-zolotovskiy-krasnoe-suhoe-13.webp` | Красностоп Золотовский | Ведерниковъ | Рубиново-красный | Красностоп Золотовский | Красное |

### `54aa8496.jpg` — rank **8**

**GT:** `golubitskoe-estate-merlo-rezerv-krasnoe-suhoe-135.webp`  
Мерло Резерв · Golubitskoe Estate · Глубокий вишнево-рубиновый · Мерло · Красное

gap12=-0.1143 · same_winery_in_top=4 · same_color_in_top=0 · same_category_in_top=4

| # | relation | file | name | winery | color | grape | category |
|--:|----------|------|------|--------|-------|-------|----------|
| 1 | `same_winery` | `golubitskoe-estate-noble-selection-red-blend-kaberne-sovinon-krasnoe-suhoe-136.webp` | Noble Selection Red Blend | Golubitskoe Estate | Красивый гранатово-красный | Каберне Совиньон | Красное |
| 2 | `same_winery` | `golubitskoe-estate-kaberne-sovinon-noble-selection-krasnoe-suhoe-133.webp` | Каберне Совиньон Noble Selection | Golubitskoe Estate | Насыщенный рубиново-вишневый | Каберне Совиньон | Красное |
| 3 | `near` | `pomeste-golubitskoe-kaberne-sovinon-rezerv-krasnoe-suhoe-143.webp` | Каберне Совиньон Резерв | Golubitskoe Estate | Глубокий рубиново-красный цвет с гранатовыми оттенками. | Каберне Совиньон | Красное |
| 4 | `near` | `golubitskoe-estate-kaberne-sovinon-rezerv-krasnoe-suhoe-125.webp` | Каберне Совиньон Резерв | Golubitskoe Estate | Темный красно-рубиновый | Каберне Совиньон | Красное |
| 5 | `other` | `zmv-koktebel-rkatsiteli-desertnoe-beloe-sladkoe-16.webp` | Ркацители десертное | ЗМВ Коктебель | Янтарный | Ркацители | Белое |

### `b5fc1c4a.jpg` — rank **22**

**GT:** `zolotoe-pole-legend-of-crimea-red-blend-kaberne-sovinon-krasnoe-suhoe-14.webp`  
Legend of Crimea "Red Blend" · Золотое Поле · Глубокий рубиновый с гранатовым оттенком · Каберне Совиньон, Каберне Фран, Мерло · Красное

gap12=-0.087 · same_winery_in_top=0 · same_color_in_top=0 · same_category_in_top=4

| # | relation | file | name | winery | color | grape | category |
|--:|----------|------|------|--------|-------|-------|----------|
| 1 | `other` | `vinodelnya-vedernikov-fantom-7030-krasnostop-zolotovskiy-krasnoe-suhoe-15.webp` | Фантом 70/30 | Ведерниковъ | Пурпурно-красный | Каберне Совиньон, Красностоп Золотовский | Красное |
| 2 | `other` | `leto-kaberne-fran-rezerv-2021-suhoe-krasnoe.webp` | LETO Каберне Фран Резерв 2021 сухое красное | LETO | Насыщенный рубиновый | Каберне Фран | Красное |
| 3 | `other` | `agrolayn-vexillum-blanc-de-noirs-pino-nuar-beloe-bryut-12.webp` | Vexillum Blanc de Noirs | Агролайн | Соломенный | Пино Нуар | Белое |
| 4 | `other` | `vinodelnya-vedernikov-fantom-5050-krasnostop-zolotovskiy-krasnoe-suhoe-145.webp` | Фантом 50/50 | Ведерниковъ | Рубиновый с гранатовым оттенком | Каберне Совиньон, Красностоп Золотовский | Красное |
| 5 | `other` | `stn-winery-arhitektor-sira-krasnoe-suhoe-12.webp` | Архитектор. Сира | STN Winery | Гранатово-рубиновый | Сира | Красное |

### `0a235276.jpg` — rank **26**

**GT:** `golubitskoe-estate-red-blend-kaberne-sovinon-krasnoe-suhoe-136.webp`  
Red Blend · Golubitskoe Estate · Глубокий красно-рубиновый · Каберне Совиньон · Красное

gap12=-0.1392 · same_winery_in_top=1 · same_color_in_top=0 · same_category_in_top=5

| # | relation | file | name | winery | color | grape | category |
|--:|----------|------|------|--------|-------|-------|----------|
| 1 | `other` | `usadba-mezyb-usadba-mezyb-merlo-krasnoe-suhoe-15.webp` | Усадьба Мезыбь. Мерло | Усадьба Мезыбь | Тёмно-рубиновый | Мерло | Красное |
| 2 | `other` | `usadba-mezyb-usadba-mezyb-kaberne-sovinon-kaberne-fran-merlo-krasnoe-suhoe-148.webp` | Усадьба Мезыбь. Каберне Совиньон, Каберне Фран, Мерло | Усадьба Мезыбь | Тёмно-рубиновый | Каберне Совиньон, Каберне Фран, Мерло | Красное |
| 3 | `other` | `leto-kaberne-fran-rezerv-2021-suhoe-krasnoe.webp` | LETO Каберне Фран Резерв 2021 сухое красное | LETO | Насыщенный рубиновый | Каберне Фран | Красное |
| 4 | `near` | `golubitskoe-estate-kaberne-sovinon-krasnoe-suhoe-137.webp` | Каберне Совиньон | Golubitskoe Estate | Темно-рубиновый с гранатовым ободком | Каберне Совиньон | Красное |
| 5 | `other` | `usadba-mezyb-usadba-mezyb-kaberne-fran-krasnoe-suhoe-145.webp` | Усадьба Мезыбь. Каберне Фран | Усадьба Мезыбь | Рубиновый с гранатовым оттенком | Каберне Фран | Красное |

### `1978bd14.jpg` — rank **44**

**GT:** `zolotoe-pole-legend-of-crimea-cabernet-sauvignon-kaberne-sovinon-krasnoe-suhoe-125.webp`  
Legend of Crimea "Cabernet Sauvignon" · Золотое Поле · Насыщенный рубиновый · Каберне Совиньон · Красное

gap12=-0.1386 · same_winery_in_top=0 · same_color_in_top=1 · same_category_in_top=1

| # | relation | file | name | winery | color | grape | category |
|--:|----------|------|------|--------|-------|-------|----------|
| 1 | `other` | `skalistyy-bereg-skb-roze-pino-nuar-beloe-ekstra-bryut-122.webp` | СКБ. Розе | Скалистый берег | Розовое золото | Пино Нуар | Белое |
| 2 | `other` | `lorio-rozovoe.webp` | ЛОРИО. Розовое | ЛОРИО -  семейная винодельня Логуновых | Лососево-розовый | Каберне Совиньон, Пино Нуар | Розовое |
| 3 | `other` | `vinodelnya-uzunov-roze-ekstra-bryut-kaberne-sovinon-rozovoe-127.webp` | Розе экстра брют | Винодельня Узунов | Бледно-розовый | Каберне Совиньон, Каберне Фран | Розовое |
| 4 | `other` | `leto-kaberne-fran-rezerv-2021-suhoe-krasnoe.webp` | LETO Каберне Фран Резерв 2021 сухое красное | LETO | Насыщенный рубиновый | Каберне Фран | Красное |
| 5 | `other` | `b-yu-rne-l-yu-bl-yu-suhoe-rozovoe.webp` | БЮРНЬЕ.ЛЮБЛЮ сухое розовое | Винодельня Бюрнье | Светло-розовый | Мерло, Сира | Розовое |

---

## Training signals (heuristic)

- High `same_winery` in miss tops → need stronger **within-winery** separation (margin / hard same-winery negatives).
- High `other` + same color/category → **lookalike packaging / line twins** across producers; near-cluster or hard-FAR mining.
- Color flips (e.g. red GT → white/sparkling tops) → preprocess / label noise / weak visual cue; check query crop quality before changing loss.
