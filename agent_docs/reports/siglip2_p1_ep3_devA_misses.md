# SigLIP2 P1 ep3 Dev-A — queries with GT not at rank 1

**Model tag:** `siglip2_p1_ep3_devA`  
**Scored:** 27  ·  **Hit@1:** 21  ·  **Miss@1:** 6  ·  **R@1:** 0.778

Slug meta from `data/owner_database/wines_integrated_updated.csv` (name · winery · color · grape · category).

---

## Aggregates on miss queries (top-k slots)

| relation | slots |
|----------|------:|
| `other` | 12 |
| `near` | 7 |
| `same_winery` | 7 |
| `GT` | 4 |

### Frequent intruders (appear in miss top-k, not GT)

| n | file | winery (from CSV) |
|--:|------|-------------------|
| 2 | `vinodelnya-byurne-krasnostop-krasnoe-suhoe-145.webp` | Винодельня Бюрнье |
| 2 | `alma-valley-shardone-beloe-suhoe-135.webp` | Alma Valley |
| 1 | `alma-valley-tempranilo-rezerv-krasnoe-suhoe-14.webp` | Alma Valley |
| 1 | `b-yu-rne-krasnostop-suhoe-krasnoe-classic.webp` | Винодельня Бюрнье |
| 1 | `b-yu-rne-sira-krasnoe-suhoe-classic.webp` | Винодельня Бюрнье |
| 1 | `b-yu-rne-malbek-krasnoe-suhoe.webp` | Винодельня Бюрнье |
| 1 | `vinodelnya-byurne-byurne-pino-blan-beloe-suhoe-14.webp` | Винодельня Бюрнье |
| 1 | `alma-valley-shardone-rezerv-beloe-suhoe-135.webp` | Alma Valley |
| 1 | `alma-valley-pino-nuar-krasnoe-suhoe-13.webp` | Alma Valley |
| 1 | `alma-valley-shiraz-sira-rezerv-krasnoe-suhoe-14.webp` | Alma Valley |
| 1 | `esse-saperavi-krasnoe-suhoe-13.webp` | ESSE |
| 1 | `esse-kaberne-sovinon-krasnoe-suhoe-14.webp` | ESSE |
| 1 | `esse-esse-sira-krasnoe-suhoe-12.webp` | ESSE |
| 1 | `esse-merlo-otbornoe-krasnoe-suhoe-13.webp` | ESSE |
| 1 | `oxana-istratova-wine-saperavi-2023-krasnoe-suhoe-13.webp` | Oxana Istratova Wine |
| 1 | `vinodelnya-vedernikov-fantom-7030-krasnostop-zolotovskiy-krasnoe-suhoe-15.webp` | Ведерниковъ |
| 1 | `sober-bash-grani-plechistik-krasnoe-suhoe-12.webp` | Собер Баш |
| 1 | `vinodelnya-vedernikov-fantom-3070-krasnostop-zolotovskiy-krasnoe-suhoe-145.webp` | Ведерниковъ |
| 1 | `belbek-risling-risling-reynskiy-beloe-suhoe-12.webp` | Бельбек |
| 1 | `chteau-le-grand-vostock-grand-karsov-shardone-beloe-suhoe-14.webp` | Château Le Grand Vostock |
| 1 | `le-k2-vassal-risling-reynskiy-beloe-suhoe-14.webp` | Le K2 |
| 1 | `leto-kaberne-fran-rezerv-2021-suhoe-krasnoe.webp` | LETO |
| 1 | `usadba-mezyb-shishka-pino-nuar-rozovoe-suhoe-115.webp` | Усадьба Мезыбь |
| 1 | `imenie-sikory-risling-pozdniy-sbor-beloe-sladkoe-13.webp` | Имение Сикоры |

### Intruder wineries

| n | winery |
|--:|--------|
| 6 | Винодельня Бюрнье |
| 6 | Alma Valley |
| 4 | ESSE |
| 2 | Ведерниковъ |
| 1 | Oxana Istratova Wine |
| 1 | Собер Баш |
| 1 | Бельбек |
| 1 | Château Le Grand Vostock |
| 1 | Le K2 |
| 1 | LETO |
| 1 | Усадьба Мезыбь |
| 1 | Имение Сикоры |

### Color GT → top candidate

| n | pattern |
|--:|---------|
| 2 | Насыщенный рубиновый цвет → Насыщенный рубиновый |
| 2 | Интенсивный рубиновый → Насыщенный рубиновый |
| 2 | Золотистый → Рубиновый |
| 2 | Интенсивный рубиново-красный с фиолетовым оттенком. → Золотистый |
| 1 | Насыщенный рубиновый цвет → Рубиновый |
| 1 | Насыщенный рубиновый цвет → Светло-золотистый |
| 1 | Интенсивный рубиновый → Гиперинтенсивный пурпурный |
| 1 | Интенсивный рубиновый → Светло-лимонный |
| 1 | Золотистый → Золотистый, сияющий цвет с яркими золотыми бликами. |
| 1 | Золотистый → Светло-золотистый |
| 1 | Насыщенный красный → Рубиново-красный |
| 1 | Насыщенный красный → Насыщенно-красный |
| 1 | Насыщенный красный → Темно-вишневый |
| 1 | Насыщенный красный → Ярко-рубиновый |
| 1 | Малиново-фиолетовый → Малиновый с пурпурным оттенком |
| 1 | Малиново-фиолетовый → Пурпурно-красный |
| 1 | Малиново-фиолетовый → Гранатовый |
| 1 | Малиново-фиолетовый → Красно-рубиновый |
| 1 | Малиново-фиолетовый → Светло-лимонный |
| 1 | Интенсивный рубиново-красный с фиолетовым оттенком. → Вино бледно-лимонного цвета. |

### Winery GT → top candidate

| n | pattern |
|--:|---------|
| 6 | Alma Valley → Alma Valley |
| 4 | Винодельня Бюрнье → Винодельня Бюрнье |
| 4 | ESSE → ESSE |
| 2 | Alma Valley → Винодельня Бюрнье |
| 2 | ESSE → Ведерниковъ |
| 1 | ESSE → Oxana Istratova Wine |
| 1 | ESSE → Собер Баш |
| 1 | ESSE → Бельбек |
| 1 | Криница → Château Le Grand Vostock |
| 1 | Криница → Le K2 |
| 1 | Криница → LETO |
| 1 | Криница → Усадьба Мезыбь |
| 1 | Криница → Имение Сикоры |

---

## Miss cards (rank > 1)

### `e2591aad.jpg` — rank **2**

**GT:** `alma-valley-tempranilo-krasnoe-suhoe-13.webp`  
Темпранильо · Alma Valley · Насыщенный рубиновый цвет · Темпранильо · Красное

gap12=-0.059 · same_winery_in_top=3 · same_color_in_top=1 · same_category_in_top=4

| # | relation | file | name | winery | color | grape | category |
|--:|----------|------|------|--------|-------|-------|----------|
| 1 | `other` | `vinodelnya-byurne-krasnostop-krasnoe-suhoe-145.webp` | БЮРНЬЕ.КРАСНОСТОП сухое красное | Винодельня Бюрнье | Насыщенный рубиновый | Красностоп | Красное |
| 2 | `GT` | `alma-valley-tempranilo-krasnoe-suhoe-13.webp` | Темпранильо | Alma Valley | Насыщенный рубиновый цвет | Темпранильо | Красное |
| 3 | `near` | `alma-valley-tempranilo-rezerv-krasnoe-suhoe-14.webp` | Темпранильо Резерв | Alma Valley | Рубиновый | Темпранильо | Красное |
| 4 | `same_winery` | `alma-valley-shardone-beloe-suhoe-135.webp` | Шардоне | Alma Valley | Светло-золотистый | Шардоне | Белое |
| 5 | `other` | `b-yu-rne-krasnostop-suhoe-krasnoe-classic.webp` | БЮРНЬЕ.КРАСНОСТОП сухое красное Classic | Винодельня Бюрнье | Насыщенный рубиновый | Красностоп | Красное |

### `e3f116c0.jpeg` — rank **3**

**GT:** `vinodelnya-byurne-merlo-krasnoe-suhoe-14.webp`  
БЮРНЬЕ.МЕРЛО сухое красное · Винодельня Бюрнье · Интенсивный рубиновый · Мерло · Красное

gap12=-0.0259 · same_winery_in_top=5 · same_color_in_top=1 · same_category_in_top=4

| # | relation | file | name | winery | color | grape | category |
|--:|----------|------|------|--------|-------|-------|----------|
| 1 | `near` | `b-yu-rne-sira-krasnoe-suhoe-classic.webp` | БЮРНЬЕ.СИРА красное сухое Classic | Винодельня Бюрнье | Насыщенный рубиновый | Сира | Красное |
| 2 | `near` | `b-yu-rne-malbek-krasnoe-suhoe.webp` | БЮРНЬЕ.МАЛЬБЕК красное сухое | Винодельня Бюрнье | Гиперинтенсивный пурпурный | Мальбек | Красное |
| 3 | `GT` | `vinodelnya-byurne-merlo-krasnoe-suhoe-14.webp` | БЮРНЬЕ.МЕРЛО сухое красное | Винодельня Бюрнье | Интенсивный рубиновый | Мерло | Красное |
| 4 | `same_winery` | `vinodelnya-byurne-krasnostop-krasnoe-suhoe-145.webp` | БЮРНЬЕ.КРАСНОСТОП сухое красное | Винодельня Бюрнье | Насыщенный рубиновый | Красностоп | Красное |
| 5 | `near` | `vinodelnya-byurne-byurne-pino-blan-beloe-suhoe-14.webp` | БЮРНЬЕ.ПИНО БЛАН сухое белое | Винодельня Бюрнье | Светло-лимонный | Пино Блан | Белое |

### `35f764ae.jpg` — rank **3**

**GT:** `alma-valley-shardone-rezerv-beloe-suhoe-14.webp`  
Шардоне Резерв · Alma Valley · Золотистый · Шардоне · Белое

gap12=-0.0956 · same_winery_in_top=5 · same_color_in_top=1 · same_category_in_top=3

| # | relation | file | name | winery | color | grape | category |
|--:|----------|------|------|--------|-------|-------|----------|
| 1 | `near` | `alma-valley-shardone-rezerv-beloe-suhoe-135.webp` | Шардоне Резерв | Alma Valley | Золотистый, сияющий цвет с яркими золотыми бликами. | Шардоне | Белое |
| 2 | `near` | `alma-valley-shardone-beloe-suhoe-135.webp` | Шардоне | Alma Valley | Светло-золотистый | Шардоне | Белое |
| 3 | `GT` | `alma-valley-shardone-rezerv-beloe-suhoe-14.webp` | Шардоне Резерв | Alma Valley | Золотистый | Шардоне | Белое |
| 4 | `same_winery` | `alma-valley-pino-nuar-krasnoe-suhoe-13.webp` | Пино Нуар | Alma Valley | Рубиновый | Пино Нуар | Красное |
| 5 | `same_winery` | `alma-valley-shiraz-sira-rezerv-krasnoe-suhoe-14.webp` | Шираз (Сира) Резерв | Alma Valley | Рубиновый | Шираз | Красное |

### `170d9123.jpeg` — rank **5**

**GT:** `esse-kaberne-otbornoe-kaberne-sovinon-krasnoe-suhoe-12.webp`  
Каберне Отборное · ESSE · Насыщенный красный · Каберне Совиньон · Красное

gap12=-0.0178 · same_winery_in_top=5 · same_color_in_top=1 · same_category_in_top=5

| # | relation | file | name | winery | color | grape | category |
|--:|----------|------|------|--------|-------|-------|----------|
| 1 | `same_winery` | `esse-saperavi-krasnoe-suhoe-13.webp` | Саперави | ESSE | Рубиново-красный | Саперави | Красное |
| 2 | `same_winery` | `esse-kaberne-sovinon-krasnoe-suhoe-14.webp` | Каберне Совиньон | ESSE | Насыщенно-красный | Каберне Совиньон | Красное |
| 3 | `same_winery` | `esse-esse-sira-krasnoe-suhoe-12.webp` | Esse Сира | ESSE | Темно-вишневый | Сира | Красное |
| 4 | `near` | `esse-merlo-otbornoe-krasnoe-suhoe-13.webp` | Мерло Отборное | ESSE | Ярко-рубиновый | Мерло | Красное |
| 5 | `GT` | `esse-kaberne-otbornoe-kaberne-sovinon-krasnoe-suhoe-12.webp` | Каберне Отборное | ESSE | Насыщенный красный | Каберне Совиньон | Красное |

### `4ea254fd.jpg` — rank **14**

**GT:** `esse-saperavi-heaven-krasnoe-suhoe-13.webp`  
Саперави Heaven · ESSE · Малиново-фиолетовый · Саперави · Красное

gap12=-0.0536 · same_winery_in_top=0 · same_color_in_top=0 · same_category_in_top=4

| # | relation | file | name | winery | color | grape | category |
|--:|----------|------|------|--------|-------|-------|----------|
| 1 | `other` | `oxana-istratova-wine-saperavi-2023-krasnoe-suhoe-13.webp` | Саперави 2023 | Oxana Istratova Wine | Малиновый с пурпурным оттенком | Саперави | Красное |
| 2 | `other` | `vinodelnya-vedernikov-fantom-7030-krasnostop-zolotovskiy-krasnoe-suhoe-15.webp` | Фантом 70/30 | Ведерниковъ | Пурпурно-красный | Каберне Совиньон, Красностоп Золотовский | Красное |
| 3 | `other` | `sober-bash-grani-plechistik-krasnoe-suhoe-12.webp` | Грани. Плечистик | Собер Баш | Гранатовый | Плечистик | Красное |
| 4 | `other` | `vinodelnya-vedernikov-fantom-3070-krasnostop-zolotovskiy-krasnoe-suhoe-145.webp` | Фантом 30/70 | Ведерниковъ | Красно-рубиновый | Каберне Совиньон, Красностоп Золотовский | Красное |
| 5 | `other` | `belbek-risling-risling-reynskiy-beloe-suhoe-12.webp` | Рислинг | Бельбек | Светло-лимонный | Рислинг Рейнский | Белое |

### `ef930b69.jpg` — rank **46**

**GT:** `vinodelnya-krinitsa-arena-sira-krasnoe-suhoe-13.webp`  
Арена · Криница · Интенсивный рубиново-красный с фиолетовым оттенком. · Сира · Красное

gap12=-0.1322 · same_winery_in_top=0 · same_color_in_top=0 · same_category_in_top=1

| # | relation | file | name | winery | color | grape | category |
|--:|----------|------|------|--------|-------|-------|----------|
| 1 | `other` | `chteau-le-grand-vostock-grand-karsov-shardone-beloe-suhoe-14.webp` | Grand Karsov | Château Le Grand Vostock | Золотистый | Шардоне | Белое |
| 2 | `other` | `le-k2-vassal-risling-reynskiy-beloe-suhoe-14.webp` | Вассал | Le K2 | Вино бледно-лимонного цвета. | Рислинг Рейнский | Белое |
| 3 | `other` | `leto-kaberne-fran-rezerv-2021-suhoe-krasnoe.webp` | LETO Каберне Фран Резерв 2021 сухое красное | LETO | Насыщенный рубиновый | Каберне Фран | Красное |
| 4 | `other` | `usadba-mezyb-shishka-pino-nuar-rozovoe-suhoe-115.webp` | Шишка. Пино Нуар | Усадьба Мезыбь | Рубиновый | Пино Нуар | Розовое |
| 5 | `other` | `imenie-sikory-risling-pozdniy-sbor-beloe-sladkoe-13.webp` | Рислинг. Поздний сбор | Имение Сикоры | Золотистый | Рислинг | Белое |

---

## Training signals (heuristic)

- High `same_winery` in miss tops → need stronger **within-winery** separation (margin / hard same-winery negatives).
- High `other` + same color/category → **lookalike packaging / line twins** across producers; near-cluster or hard-FAR mining.
- Color flips (e.g. red GT → white/sparkling tops) → preprocess / label noise / weak visual cue; check query crop quality before changing loss.
