# Top-5 occupants Dev-A — who shows up in the shortlist

Не SKU×SKU confusion matrix (слишком разрежена), а **частоты попадания в top-5** по 27 query.
Слоты: 27×5 = 135. Отношение кандидата к GT: `GT` / `near_same_group` / `same_winery` / `other`.

## Colab Phase1 e8

### Состав top-5 слотов (все 135)

| relation to GT | count | % |
|----------------|------:|--:|
| `GT` | 23 | 17.0 |
| `near_same_group` | 35 | 25.9 |
| `same_winery` | 19 | 14.1 |
| `other` | 58 | 43.0 |

### Самые частые **intruders** (в top-5, но не GT этого query)

| n | catalog file | winery |
|--:|--------------|--------|
| 3 | `agora-saperavi.webp` | 031_AGORA WINERY |
| 3 | `alma-valley-shiraz-krasnoe-suhoe-13.webp` | 039_Alma Valley |
| 2 | `agora-pino-nuar.webp` | 031_AGORA WINERY |
| 2 | `belbek-belbek-roze-pino-nuar-rozovoe-suhoe-129.webp` | 039_Бельбек |
| 2 | `millstream-cellar-select-saperavi.webp` | 010_MILLSTREAM |
| 2 | `millstream-cellar-select-blend-avtohtonov.webp` | 010_MILLSTREAM |
| 2 | `millstream-cellar-select-kaberne-sovinon.webp` | 010_MILLSTREAM |
| 2 | `chateau-de-talu-ruzh-kaberne-sovinon-krasnoe-suhoe-14.webp` | 026_Chateau de Talu |
| 2 | `chateau-de-talu-roze-kaberne-sovinon-rozovoe-suhoe-14.webp` | 026_Chateau de Talu |
| 2 | `sober-bash-grani-plechistik-krasnoe-suhoe-12.webp` | 035_Собер Баш |
| 2 | `chateau-de-talu-blan-semilon-beloe-suhoe-127.webp` | 026_Chateau de Talu |
| 2 | `alma-valley-shardone-beloe-suhoe-135.webp` | 039_Alma Valley |
| 2 | `riesling.webp` | 031_WINEMAFIA |
| 2 | `bogovich-wine-vineyard-kaberne-fran-krasnoe-suhoe-135.webp` | 010_Bogovich Wine & Vineyard |
| 1 | `agora-muskat.webp` | 031_AGORA WINERY |

### Самые частые winery среди intruders

| n | winery |
|--:|--------|
| 10 | 039_Alma Valley |
| 9 | 026_Chateau de Talu |
| 9 | 042_Массандра |
| 8 | 096_Кубань-Вино |
| 7 | 052_ESSE |
| 7 | 010_MILLSTREAM |
| 7 | 019_Винодельня Бюрнье |
| 7 | 031_WINEMAFIA |
| 6 | 031_AGORA WINERY |
| 5 | 039_Бельбек |

## Colab Phase2 e1 (best)

### Состав top-5 слотов (все 135)

| relation to GT | count | % |
|----------------|------:|--:|
| `GT` | 21 | 15.6 |
| `near_same_group` | 35 | 25.9 |
| `same_winery` | 22 | 16.3 |
| `other` | 57 | 42.2 |

### Самые частые **intruders** (в top-5, но не GT этого query)

| n | catalog file | winery |
|--:|--------------|--------|
| 3 | `agora-pino-nuar.webp` | 031_AGORA WINERY |
| 3 | `millstream-cellar-select-saperavi.webp` | 010_MILLSTREAM |
| 3 | `chateau-de-talu-blan-semilon-beloe-suhoe-127.webp` | 026_Chateau de Talu |
| 2 | `agora-saperavi.webp` | 031_AGORA WINERY |
| 2 | `millstream-cellar-select-blend-avtohtonov.webp` | 010_MILLSTREAM |
| 2 | `chateau-de-talu-ruzh-kaberne-sovinon-krasnoe-suhoe-14.webp` | 026_Chateau de Talu |
| 2 | `chateau-de-talu-roze-kaberne-sovinon-rozovoe-suhoe-14.webp` | 026_Chateau de Talu |
| 2 | `alma-valley-shiraz-krasnoe-suhoe-13.webp` | 039_Alma Valley |
| 2 | `riesling.webp` | 031_WINEMAFIA |
| 2 | `bogovich-wine-vineyard-kaberne-fran-krasnoe-suhoe-135.webp` | 010_Bogovich Wine & Vineyard |
| 1 | `agora-muskat.webp` | 031_AGORA WINERY |
| 1 | `belbek-belbek-risling-rezerv-beloe-suhoe-13.webp` | 039_Бельбек |
| 1 | `winemaker-selection.webp` | 015_Инкерманский ЗМВ |
| 1 | `abrau-dyurso-imperial-brut-vintage-shardone-beloe-bryut-1…` | 050_Абрау-Дюрсо |
| 1 | `abrau-dyurso-imperial-brut-rose-pino-nuar-rozovoe-bryut-1…` | 050_Абрау-Дюрсо |

### Самые частые winery среди intruders

| n | winery |
|--:|--------|
| 10 | 042_Массандра |
| 10 | 039_Alma Valley |
| 9 | 026_Chateau de Talu |
| 8 | 096_Кубань-Вино |
| 7 | 039_Бельбек |
| 7 | 010_MILLSTREAM |
| 6 | 031_AGORA WINERY |
| 6 | 019_Винодельня Бюрнье |
| 6 | 052_ESSE |
| 6 | 031_WINEMAFIA |

## ONNX Phase1

### Состав top-5 слотов (все 135)

| relation to GT | count | % |
|----------------|------:|--:|
| `GT` | 22 | 16.3 |
| `near_same_group` | 38 | 28.1 |
| `same_winery` | 22 | 16.3 |
| `other` | 53 | 39.3 |

### Самые частые **intruders** (в top-5, но не GT этого query)

| n | catalog file | winery |
|--:|--------------|--------|
| 3 | `agora-saperavi.webp` | 031_AGORA WINERY |
| 3 | `chateau-de-talu-roze-kaberne-sovinon-rozovoe-suhoe-14.webp` | 026_Chateau de Talu |
| 3 | `alma-valley-shardone-beloe-suhoe-135.webp` | 039_Alma Valley |
| 2 | `belbek-belbek-fiolent-muskat-beloe-polusladkoe-125.webp` | 039_Бельбек |
| 2 | `vinodelnya-uzunov-bunt-tsitronnyy-magaracha-beloe-suhoe-1…` | 015_Винодельня Узунов |
| 2 | `bogovich-wine-vineyard-pino-nuar-krasnoe-suhoe-125.webp` | 010_Bogovich Wine & Vineyard |
| 2 | `millstream-cellar-select-krasnostop-zolotovskij.webp` | 010_MILLSTREAM |
| 2 | `portvejn-surozh.webp` | 042_Массандра |
| 2 | `massandra-portveyn-belyy-gurzuf-kokur-belyy-beloe-sladkoe…` | 042_Массандра |
| 1 | `agora-muskat.webp` | 031_AGORA WINERY |
| 1 | `belbek-sira-rezerv-krasnoe-suhoe-132.webp` | 039_Бельбек |
| 1 | `winemaker-selection.webp` | 015_Инкерманский ЗМВ |
| 1 | `fanagoriya-dekanter-kaberne-fran-2019-krasnoe-suhoe-13.we…` | 100_Фанагория |
| 1 | `vinodelnya-raevskoe-renessans-belyy-blend-risling-beloe-s…` | 023_Раевское |
| 1 | `fanagoriya-dekanter-riesling-2020-risling-reynskiy-beloe-…` | 100_Фанагория |

### Самые частые winery среди intruders

| n | winery |
|--:|--------|
| 12 | 039_Alma Valley |
| 9 | 052_ESSE |
| 9 | 042_Массандра |
| 8 | 096_Кубань-Вино |
| 7 | 026_Chateau de Talu |
| 6 | 039_Бельбек |
| 5 | 019_Винодельня Бюрнье |
| 4 | 031_AGORA WINERY |
| 4 | 100_Фанагория |
| 4 | 010_MILLSTREAM |

## ONNX Phase2

### Состав top-5 слотов (все 135)

| relation to GT | count | % |
|----------------|------:|--:|
| `GT` | 22 | 16.3 |
| `near_same_group` | 33 | 24.4 |
| `same_winery` | 26 | 19.3 |
| `other` | 54 | 40.0 |

### Самые частые **intruders** (в top-5, но не GT этого query)

| n | catalog file | winery |
|--:|--------------|--------|
| 3 | `lesnaya-proseka.webp` | 096_Кубань-Вино |
| 3 | `chateau-de-talu-roze-kaberne-sovinon-rozovoe-suhoe-14.webp` | 026_Chateau de Talu |
| 2 | `belbek-belbek-fiolent-muskat-beloe-polusladkoe-125.webp` | 039_Бельбек |
| 2 | `vinodelnya-batrak-contadina-merlo-krasnoe-suhoe-14.webp` | 019_Винодельня Батрак |
| 2 | `vinodelnya-uzunov-bunt-tsitronnyy-magaracha-beloe-suhoe-1…` | 015_Винодельня Узунов |
| 2 | `millstream-cellar-select-blend-avtohtonov.webp` | 010_MILLSTREAM |
| 2 | `millstream-cellar-select-saperavi.webp` | 010_MILLSTREAM |
| 2 | `chateau-de-talu-blan-semilon-beloe-suhoe-127.webp` | 026_Chateau de Talu |
| 2 | `portvejn-surozh.webp` | 042_Массандра |
| 2 | `massandra-portveyn-belyy-gurzuf-kokur-belyy-beloe-sladkoe…` | 042_Массандра |
| 2 | `alma-valley-shiraz-krasnoe-suhoe-13.webp` | 039_Alma Valley |
| 2 | `alma-valley-shardone-beloe-suhoe-135.webp` | 039_Alma Valley |
| 1 | `agora-muskat.webp` | 031_AGORA WINERY |
| 1 | `makitra-selection.webp` | 096_Кубань-Вино |
| 1 | `vinodelnya-molchanova-krasnostop-zolotovskiy-krasnoe-suho…` | 003_Винодельня Молчанова |

### Самые частые winery среди intruders

| n | winery |
|--:|--------|
| 14 | 096_Кубань-Вино |
| 13 | 039_Alma Valley |
| 9 | 042_Массандра |
| 8 | 052_ESSE |
| 8 | 026_Chateau de Talu |
| 6 | 039_Бельбек |
| 6 | 010_MILLSTREAM |
| 5 | 100_Фанагория |
| 5 | 050_Абрау-Дюрсо |
| 4 | 019_Винодельня Батрак |

## P1 vs P2 — смесь слотов top-5 (Colab)

| relation | P1 e8 | P2 e1 | Δ |
|----------|------:|------:|--:|
| `GT` | 23 | 21 | -2 |
| `near_same_group` | 35 | 35 | +0 |
| `same_winery` | 19 | 22 | +3 |
| `other` | 58 | 57 | -1 |

## P1 vs P2 — смесь слотов top-5 (ONNX)

| relation | ONNX P1 | ONNX P2 | Δ |
|----------|--------:|--------:|--:|
| `GT` | 22 | 22 | +0 |
| `near_same_group` | 38 | 33 | -5 |
| `same_winery` | 22 | 26 | +4 |
| `other` | 53 | 54 | +1 |

## Intruders, общие для Colab P1 и P2 (частота P1 / P2)

| P1 | P2 | file | winery |
|---:|---:|------|--------|
| 3 | 2 | `alma-valley-shiraz-krasnoe-suhoe-13.webp` | 039_Alma Valley |
| 2 | 3 | `millstream-cellar-select-saperavi.webp` | 010_MILLSTREAM |
| 2 | 3 | `chateau-de-talu-blan-semilon-beloe-suhoe-127.webp` | 026_Chateau de Talu |
| 2 | 3 | `agora-pino-nuar.webp` | 031_AGORA WINERY |
| 3 | 2 | `agora-saperavi.webp` | 031_AGORA WINERY |
| 2 | 2 | `chateau-de-talu-ruzh-kaberne-sovinon-krasnoe-suhoe-14.webp` | 026_Chateau de Talu |
| 2 | 2 | `millstream-cellar-select-blend-avtohtonov.webp` | 010_MILLSTREAM |
| 2 | 2 | `riesling.webp` | 031_WINEMAFIA |
| 2 | 2 | `chateau-de-talu-roze-kaberne-sovinon-rozovoe-suhoe-14.webp` | 026_Chateau de Talu |
| 2 | 2 | `bogovich-wine-vineyard-kaberne-fran-krasnoe-suhoe-135.webp` | 010_Bogovich Wine & Vineyard |
| 2 | 1 | `belbek-belbek-roze-pino-nuar-rozovoe-suhoe-129.webp` | 039_Бельбек |
| 1 | 1 | `millstream-cellar-select-krasnostop-zolotovskij.webp` | 010_MILLSTREAM |
| 1 | 1 | `winemaker-selection.webp` | 015_Инкерманский ЗМВ |
| 1 | 1 | `agora-muskat.webp` | 031_AGORA WINERY |
| 1 | 1 | `fanagoriya-dekanter-pino-nuar-2020-krasnoe-suhoe-135.webp` | 100_Фанагория |
| 1 | 1 | `fanagoriya-dekanter-kaberne-sovinon-2018-krasnoe-suhoe-14…` | 100_Фанагория |
| 1 | 1 | `belbek-belbek-kaberne-fran-krasnoe-suhoe-13.webp` | 039_Бельбек |

## Intruders, общие для ONNX P1 и P2

| P1 | P2 | file | winery |
|---:|---:|------|--------|
| 3 | 3 | `chateau-de-talu-roze-kaberne-sovinon-rozovoe-suhoe-14.webp` | 026_Chateau de Talu |
| 3 | 2 | `alma-valley-shardone-beloe-suhoe-135.webp` | 039_Alma Valley |
| 2 | 2 | `belbek-belbek-fiolent-muskat-beloe-polusladkoe-125.webp` | 039_Бельбек |
| 2 | 2 | `massandra-portveyn-belyy-gurzuf-kokur-belyy-beloe-sladkoe…` | 042_Массандра |
| 2 | 2 | `portvejn-surozh.webp` | 042_Массандра |
| 2 | 2 | `vinodelnya-uzunov-bunt-tsitronnyy-magaracha-beloe-suhoe-1…` | 015_Винодельня Узунов |
| 1 | 2 | `millstream-cellar-select-saperavi.webp` | 010_MILLSTREAM |
| 1 | 2 | `millstream-cellar-select-blend-avtohtonov.webp` | 010_MILLSTREAM |
| 2 | 1 | `bogovich-wine-vineyard-pino-nuar-krasnoe-suhoe-125.webp` | 010_Bogovich Wine & Vineyard |
| 1 | 1 | `winemaker-selection.webp` | 015_Инкерманский ЗМВ |
| 1 | 1 | `fanagoriya-dekanter-riesling-2020-risling-reynskiy-beloe-…` | 100_Фанагория |
| 1 | 1 | `esse-pino-gri-blash-rozovoe-suhoe-125.webp` | 052_ESSE |
| 1 | 1 | `fanagoriya-dekanter-kaberne-fran-2019-krasnoe-suhoe-13.we…` | 100_Фанагория |
| 1 | 1 | `belbek-merlo-krasnoe-suhoe-13.webp` | 039_Бельбек |
| 1 | 1 | `agora-muskat.webp` | 031_AGORA WINERY |

## Reading for hard-negatives

Если hard-FAR «сработал бы» как задумано, ожидали бы меньше `other`/`same_winery` lookalikes в top-5 
или сдвиг состава intruders. По факту смесь слотов P1≈P2 (сдвиги на единицы при 135 слотах).
Это совместимо с гипотезой «негативы почти не изменили shortlist», но **не доказывает** причину 
(нет ablation без hard term; Colab R@5 всё же −2 query на best P2).
