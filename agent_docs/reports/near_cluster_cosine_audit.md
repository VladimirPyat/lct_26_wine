# Near-cluster cosine audit (Phase1 ONNX)

- onnx: `bin/dinov2_wine_phase1.onnx`
- root: `/work/lct_vine_final/data/train_dataset/near_clusters`
- threshold: **0.8** (flag if any pair &lt; threshold)
- clusters scanned (≥2 imgs, excl. singletons): **390**
- skipped (&lt;2 imgs): 4
- **flagged: 309**

## Flagged (weakest pair first)

| min cos | n | path | pair |
|--------:|--:|------|------|
| -0.146 | 5 | `013_Солнечная долина/2` | `beloe-suhoe.webp` ↔ `solnechnaya-dolina-meganom-kokur-beloe-bryut.webp` |
| -0.067 | 13 | `052_ESSE/all__cluster_06_n2` | `esse-ridicule-sira-krasnoe-suhoe-125.webp` ↔ `esse-saperavi-heaven-krasnoe-suhoe-13.webp` |
| -0.000 | 7 | `007_Rem Akchurin/1` | `rem-akchurin-rem-akchurin-pino-nuar-roze-rozovoe-suhoe-14.webp` ↔ `rem-akchurin-shardone-beloe-bryut-14.webp` |
| 0.002 | 8 | `013_Солнечная долина/1` | `privat.webp` ↔ `sary-pandas-vyderzhannoe.webp` |
| 0.007 | 4 | `004_Николаев и сыновья/group` | `nikolaev-i-synovya-flamingo-malbek-rozovoe-suhoe-125.webp` ↔ `nikolaev-i-synovya-pino-nuar-krasnoe-suhoe-125.webp` |
| 0.015 | 5 | `005_Винодельня Марко/group` | `vinodelnya-marko-assamblyazh-kaberne-sovinon-krasnoe-suhoe-14.webp` ↔ `vinodelnya-marko-vione-beloe-suhoe-12.webp` |
| 0.031 | 3 | `009_Литавщук. Litavshchuk vineyards & winery/2` | `pino-nuar-premium.webp` ↔ `rubin-premium.webp` |
| 0.034 | 4 | `004_Uva Vallis/group` | `uva-vallis-risling.webp` ↔ `uva-vallis-sovinon-blan.webp` |
| 0.051 | 5 | `006_Винодельня Братьев Мельниковых/2` | `kokur-2025.webp` ↔ `vinodelnya-bratev-melnikovyh-kaberne-sovinon-kaberne-fran-dva-brata-krasnoe-suhoe-145.webp` |
| 0.076 | 4 | `012_STN Winery/1` | `stn-winery-muskat-beloe-suhoe-115.webp` ↔ `stn-winery-syrah-sira-krasnoe-suhoe-13.webp` |
| 0.076 | 5 | `012_Gunko Winery/2` | `gunko-winery-monumental-saperavi-krasnoe-suhoe-145.webp` ↔ `gunko-winery-sovinon-blan-gunko-winery-beloe-suhoe-135.webp` |
| 0.095 | 4 | `048_Шато Пино/2` | `koldun-beloe-suhoe.webp` ↔ `shato-pino-koldun-rezerv-kaberne-sovinon-krasnoe-suhoe-14.webp` |
| 0.096 | 4 | `004_В2Р/group` | `v2r-podnyat-parusa-kaberne-sovinon-krasnoe-suhoe-125.webp` ↔ `v2r-sovinon-blan-beloe-suhoe-13.webp` |
| 0.098 | 7 | `010_ВайнКрафт/1` | `vaynkraft-aligote-beloe-suhoe-125.webp` ↔ `vaynkraft-traminer-oranzh-2-traminer-rozovyy-oranzhevoe-suhoe-125.webp` |
| 0.108 | 4 | `012_STN Winery/2` | `stn-winery-chardonnay-vol2-shardone-beloe-suhoe-105.webp` ↔ `stn-winery-wiess-risling-beloe-suhoe-12.webp` |
| 0.112 | 5 | `046_Валерий Захарьин/all__cluster_04_n4` | `valeriy-zaharin-aligote-burlyuk-beloe-bryut-115.webp` ↔ `valeriy-zaharin-kaberne-fran-burlyuk-krasnoe-suhoe-13.webp` |
| 0.118 | 3 | `003_One Barrel (Уан Баррел)/group` | `cabernet-franc-2024-one-barrel-by-dmitry-maslov-kaberne-fran-2024-uan-barrel-dmitrij-maslov.webp` ↔ `one-barrel-uan-barrel.webp` |
| 0.120 | 4 | `004_Villa di Alma/group` | `villa-di-alma-ekstra-bryut-kokur-beloe-125.webp` ↔ `villa-di-alma-pti-verdo-krasnoe-suhoe-125.webp` |
| 0.122 | 4 | `009_Le K2/1` | `le-k2-temnaya-roza-sira-rozovoe-suhoe-13.webp` ↔ `lebedushka.webp` |
| 0.135 | 6 | `025_Château Le Grand Vostock/cluster_01_n6` | `chteau-le-grand-vostock-cadet-karsov-shardone-beloe-suhoe-135.webp` ↔ `chteau-le-grand-vostock-chardonnay-reserve-shardone-beloe-suhoe-14.webp` |
| 0.139 | 11 | `052_ESSE/all__cluster_00_n10` | `esse-brut-zero-dosage-shardone-beloe-ekstra-bryut-135.webp` ↔ `esse-esse-rose-zero-dosage-shardone-rozovoe-ekstra-bryut-115.webp` |
| 0.141 | 3 | `096_Кубань-Вино/2` | `kuban-vino-aristov-kyuve-aleksandr-blanc-de-blancs-36-shardone-beloe-ekstra-bryut-12.webp` ↔ `kuban-vino-aristov-kyuve-aleksandr-rose-de-pinot-pino-nuar-rozovoe-ekstra-bryut-12.webp` |
| 0.143 | 5 | `005_GAVRAS/group` | `gavras-areni-krasnoe-suhoe-13.webp` ↔ `gavras-chardonnay-shardone-beloe-suhoe-13.webp` |
| 0.150 | 6 | `092_Мысхако/other__cluster_00_n11` | `myshako-igristoe-beloe-polusladkoe.webp` ↔ `vinodelnya-myshako-flute-blaufrankish-rozovoe-bryut-126.webp` |
| 0.150 | 4 | `010_Bogovich Wine & Vineyard/2` | `bogovich-wine-vineyard-kaberne-fran-krasnoe-suhoe-135.webp` ↔ `bogovich-wine-vineyard-klassika-pino-nuar-krasnoe-suhoe-125.webp` |
| 0.154 | 3 | `003_Левокумское/group` | `levokumskoe-beloe-rkatsiteli-suhoe-10.webp` ↔ `levokumskoe-rkatsiteli-beloe-suhoe-10.webp` |
| 0.164 | 5 | `005_Винодельня Константина Дзитоева/group` | `vinodelnya-konstantina-dzitoeva-kd-bryut-shardone-beloe-115.webp` ↔ `vinodelnya-konstantina-dzitoeva-kion-kaberne-sovinon-krasnoe-suhoe-145.webp` |
| 0.164 | 7 | `096_Кубань-Вино/aristov__cluster_01_n3` | `aristov-anima-millesimato-beloe-bryut.webp` ↔ `kuban-vino-aristov-anima-pino-nero-sandzhoveze-pino-nuar-krasnoe-suhoe-125.webp` |
| 0.165 | 7 | `050_Абрау-Дюрсо/other__cluster_03_n4` | `abrau-dyurso-pino-nuar-krasnoe-suhoe-125.webp` ↔ `abrau-dyurso-risling-beloe-suhoe-12.webp` |
| 0.166 | 13 | `019_Винодельня Бюрнье/2` | `vinodelnya-byurne-kaberne-sovinon-krasnoe-suhoe-135.webp` ↔ `vinodelnya-byurne-sira-krasnoe-suhoe-135.webp` |
| 0.166 | 3 | `013_Винодельня Жаков/2` | `vinodelnya-zhakov-kokurkod-beloe-suhoe-118.webp` ↔ `vinodelnya-zhakov-neoranzh-vostorg-beloe-suhoe-123.webp` |
| 0.169 | 6 | `015_Винодельня Узунов/1` | `vinodelnya-uzunov-aligote-beloe-suhoe-127.webp` ↔ `vinodelnya-uzunov-krasa-kaberne-sovinon-krasnoe-suhoe-125.webp` |
| 0.169 | 5 | `005_Дача Сердюка/group` | `dacha-serdyuka-saperavi-saperavi-severnyy-krasnoe-suhoe-14.webp` ↔ `dacha-serdyuka-sibirkovyy-beloe-suhoe-135.webp` |
| 0.176 | 8 | `015_Винодельня Узунов/3` | `vinodelnya-uzunov-mono-krasnostop-krasnostop-zolotovskiy-krasnoe-suhoe-139.webp` ↔ `vinodelnya-uzunov-rash-risling-beloe-suhoe-127.webp` |
| 0.181 | 5 | `009_Le K2/2` | `le-k2-v-glubine-shardone-beloe-suhoe-13.webp` ↔ `le-k2-v-tumane-sovinon-blan-beloe-suhoe-127.webp` |
| 0.201 | 8 | `011_Domaine de la Vivandiere/1` | `domaine-de-la-vivandiere-pino-nuar-roze-rozovoe-suhoe-122.webp` ↔ `domaine-de-la-vivandiere-senso-roze-rozovoe-suhoe-126.webp` |
| 0.202 | 11 | `016_LETO/1` | `leto-kaberne-fran-2021-suhoe-krasnoe.webp` ↔ `leto-risling-2024-polusuhoe-vino.webp` |
| 0.202 | 8 | `059_Дербент Вино/derbent_vino__cluster_00_n7` | `derbent-vino-desono-rkatsiteli-oranzh-beloe-suhoe-125.webp` ↔ `derbent-vino-desono-saperavi-roze-rozovoe-suhoe-125.webp` |
| 0.204 | 4 | `017_Реликта/1` | `relikta-relikta-dekabrskiy-krasnoe-polusladkoe-125.webp` ↔ `relikta-relikta-pervenets-pervenets-magaracha-beloe-suhoe-12.webp` |
| 0.205 | 6 | `046_Валерий Захарьин/all__cluster_03_n4` | `valeriy-zaharin-bakkal-su-muskat-ottonel-beloe-polusladkoe-115.webp` ↔ `valeriy-zaharin-bakkal-su-saperavi-bastardo-kaberne-sovinon-krasnoe-polusladkoe-11.webp` |
| 0.211 | 5 | `005_Uppa Winery/group` | `uppa-winery-kokur-kokur-belyy-beloe-suhoe-12.webp` ↔ `uppa-winery-pavel-shvets-cabernet-sauvignon-merlot-kaberne-sovinon-krasnoe-suhoe-14.webp` |
| 0.211 | 7 | `008_Цимлянские вина/1` | `czimlyanskoe-bianka.webp` ↔ `kyuve-czimlyanskij-chernyj-i-krasnostop-zolotoj.webp` |
| 0.219 | 3 | `052_ESSE/0` | `esse-prirodno-polusladkoe-krasnoe-merlo-13.webp` ↔ `esse-roze-kaberne-sovinon-rozovoe-suhoe-135.webp` |
| 0.221 | 8 | `019_Золотое Поле/3` | `zolotoe-pole-legend-of-crimea-muscat-ottonel-muskat-ottonel-beloe-suhoe-14.webp` ↔ `zolotoe-pole-legend-of-crimea-red-blend-kaberne-sovinon-krasnoe-suhoe-14.webp` |
| 0.223 | 2 | `011_Domaine de la Vivandiere/2` | `domaine-de-la-vivandiere-vn-beloe-aligote-suhoe-131.webp` ↔ `domaine-de-la-vivandiere-vn-krasnoe-pino-nuar-suhoe-12.webp` |
| 0.223 | 14 | `019_Галицкий и Галицкий/1` | `le-general-hiver.webp` ↔ `petrouchka.webp` |
| 0.224 | 6 | `010_Bogovich Wine & Vineyard/1` | `bogovich-wine-vineyard-faina-sovinon-zelenyy-beloe-suhoe-113.webp` ↔ `bogovich-wine-vineyard-merlo-krasnoe-suhoe-14.webp` |
| 0.227 | 5 | `019_Скалистый берег/2` | `skalistyy-bereg-pesn-holmov-merlo-krasnoe-suhoe-145.webp` ↔ `skalistyy-bereg-shyopot-tsvetov-risling-beloe-suhoe-109.webp` |
| 0.229 | 3 | `031_AGORA WINERY/4` | `blush-mirage-rkacziteli-shiraz.webp` ↔ `blush-mirage-sovinon-zelyonyj.webp` |
| 0.232 | 10 | `015_Chateau Andre/1` | `chateau-andre-aligote-beloe-suhoe-13.webp` ↔ `chateau-andre-tsvaygelt-tsvaygelt-tamanskiy-rozovoe-suhoe-13.webp` |
| 0.235 | 3 | `031_WINEMAFIA/all__cluster_02_n2` | `arie-riserva.webp` ↔ `arie.webp` |
| 0.238 | 3 | `096_Кубань-Вино/vysokiy_bereg__cluster_00_n8` | `kuban-vino-vysokiy-bereg-merlo-krasnoe-suhoe-135.webp` ↔ `vysokij-bereg-czvajgelt.webp` |
| 0.239 | 2 | `096_Кубань-Вино/chateau_tamagne__1` | `chateau-tamagne-eno-amber.webp` ↔ `chateau-tamagne-eno-traminer-i-shardone.webp` |
| 0.240 | 10 | `020_Belmas Winery/1` | `belmas-winery-cabernet-sauvignon-rose-belmas-kaberne-sovinon-rozovoe-suhoe-13.webp` ↔ `belmas-winery-risling-beloe-suhoe-135.webp` |
| 0.242 | 9 | `043_Новый Свет. Дом шампанских вин/novyj_svet__cluster_00_n13` | `novyy-svet-dom-shampanskih-vin-rossiyskoe-shampanskoe-kollektsionnoe-ekstra-bryut-beloe-novyy-svet-blan-de-nuar-pino-nuar-13.webp` ↔ `novyy-svet-dom-shampanskih-vin-rossiyskoe-shampanskoe-vyderzhannoe-bryut-rozovoe-novyy-svet-kaberne-kaberne-sovinon-11.webp` |
| 0.246 | 3 | `096_Кубань-Вино/fleur_du_sud__cluster_00_n3` | `kuban-vino-flyor-dyu-syud-blan-de-tamane-tsvetochnyy-beloe-suhoe-115.webp` ↔ `kuban-vino-flyor-dyu-syud-ruzh-de-tamane-rubin-golodrigi-krasnoe-suhoe-12.webp` |
| 0.248 | 4 | `017_Усадьба Дивноморское/2` | `usadba-divnomorskoe-blanc-de-blancs-shardone-beloe-ekstra-bryut-12.webp` ↔ `usadba-divnomorskoe-maris-blanc-de-blanc-extra-brut-shardone-beloe-ekstra-bryut-105.webp` |
| 0.248 | 7 | `050_Абрау-Дюрсо/abrau_estates__cluster_00_n7` | `abrau-dyurso-abrau-estates-amurskiy-potapenko-krasnoe-suhoe-105.webp` ↔ `abrau-dyurso-abrau-estates-kaberne-po-belomu-kaberne-sovinon-beloe-suhoe-105.webp` |
| 0.248 | 9 | `019_Скалистый берег/3` | `skalistyy-bereg-skalistyy-bereg-kaberne-sovinon-krasnoe-suhoe-15.webp` ↔ `skalistyy-bereg-skalistyy-bereg-risling-beloe-suhoe-113.webp` |
| 0.251 | 7 | `052_ESSE/all__cluster_04_n5` | `esse-merlo-otbornoe-krasnoe-suhoe-13.webp` ↔ `esse-muskat-belyy-beloe-suhoe-135.webp` |
| 0.255 | 3 | `019_Винодельня Бюрнье/1` | `vinodelnya-byurne-lyublyu-beloe-shardone-suhoe-135.webp` ↔ `vinodelnya-byurne-lyublyu-krasnoe-kaberne-fran-suhoe-135.webp` |
| 0.261 | 3 | `003_Oxana Istratova Wine/group` | `oxana-istratova-wine-saperavi-2023-krasnoe-suhoe-13.webp` ↔ `oxana-istratova-wine-vione-2023-oranzhevoe-suhoe-119.webp` |
| 0.264 | 7 | `039_Бельбек/all__cluster_04_n4` | `belbek-belbek-merlo-krasnoe-suhoe-129.webp` ↔ `belbek-pino-nuar-roze-rozovoe-suhoe-115.webp` |
| 0.264 | 10 | `021_Имение Сикоры/cluster_00_n11` | `imenie-sikory-merlo-sikory-krasnoe-suhoe-13.webp` ↔ `imenie-sikory-risling-semeynyy-rezerv-risling-reynskiy-beloe-suhoe-13.webp` |
| 0.267 | 9 | `031_Golubitskoe Estate/all__cluster_00_n7` | `golubitskoe-estate-tte-de-cheval-blanc-de-blancs-shardone-beloe-bryut-12.webp` ↔ `golubitskoe-estate-tte-de-cheval-reserve-risling-beloe-bryut-125.webp` |
| 0.268 | 7 | `031_Golubitskoe Estate/all__cluster_01_n6` | `golubitskoe-estate-red-blend-kaberne-sovinon-krasnoe-suhoe-136.webp` ↔ `golubitskoe-estate-risling-oranzh-risling-reynskiy-oranzhevoe-suhoe-13.webp` |
| 0.279 | 4 | `021_Denisov Winery/1` | `denisov-winery-petnat-risling-beloe-ekstra-bryut-10.webp` ↔ `denisov-winery-petnat-saperavi-severnyy-rozovoe-ekstra-bryut-105.webp` |
| 0.282 | 6 | `006_Chateau Cachalot/1` | `chateau-cachalot-muskat-blan-muskat-belyy-beloe-suhoe-117.webp` ↔ `chateau-cachalot-pino-nuar-krasnoe-suhoe-12.webp` |
| 0.284 | 4 | `004_Благолюбов/group` | `blagolyubov-sovinon-blan-beloe-suhoe-125.webp` ↔ `blagolyubov-stanichnoe-stanichnyy-beloe-suhoe-12.webp` |
| 0.285 | 4 | `019_Скалистый берег/1` | `blan-de-blan.webp` ↔ `grand-kyuve.webp` |
| 0.285 | 5 | `027_AYA Organic Wine & Vineyards/cluster_02_n3` | `aya-organic-wine-vineyards-purity-in-chenin-blanc-shenen-blan-beloe-suhoe-11.webp` ↔ `aya-organic-wine-vineyards-purity-in-trinity-pino-nuar-rozovoe-suhoe-13.webp` |
| 0.289 | 6 | `006_Nesterov Winery/1` | `nesterov-winery-krasnostop-rubin-klere-krasnostop-zolotovskiy-rozovoe-suhoe-11.webp` ↔ `nesterov-winery-risling-reynskiy-beloe-suhoe-12.webp` |
| 0.290 | 6 | `043_Ведерниковъ/other__cluster_00_n13` | `vinodelnya-vedernikov-krasnostop-zolotovskiy-rezerv-krasnoe-suhoe-15.webp` ↔ `vinodelnya-vedernikov-tsimlyanskiy-chernyy-bryut-roze-rozovoe-129.webp` |
| 0.291 | 6 | `100_Фанагория/cluster_07_n3` | `fanagoriya-formula-q-kaberne-sovinon-krasnoe-suhoe-135.webp` ↔ `fanagoriya-q-bordeaux-blend-kaberne-sovinon-krasnoe-suhoe-135.webp` |
| 0.291 | 8 | `017_Усадьба Дивноморское/1` | `usadba-divnomorskoe-grande-cuvee-shardone-beloe-bryut-125.webp` ↔ `usadba-divnomorskoe-west-hill-blend-kaberne-sovinon-krasnoe-suhoe-145.webp` |
| 0.292 | 4 | `100_Фанагория/cluster_08_n3` | `fanagoriya-alveus-ultra-cuvee-brut-shardone-beloe-bryut-12.webp` ↔ `fanagoriya-alveus-ultra-cuvee-ekstra-bryut-beloe-risling-reynskiy-12.webp` |
| 0.294 | 5 | `027_Золотая Балка/cluster_03_n3` | `rozovoe-bryut-spumante.webp` ↔ `zolotaya-balka-zb-spumante-brut-risling-beloe-bryut-125.webp` |
| 0.300 | 3 | `096_Кубань-Вино/chateau_tamagne__2` | `chateau-tamagne-select-blanc.webp` ↔ `kuban-vino-shato-tamane-selekt-ruzh-saperavi-krasnoe-suhoe-125.webp` |
| 0.300 | 7 | `015_Инкерманский ЗМВ/3` | `inkermanskiy-zmv-inkerman-polusladkoe-roze-aligote-rozovoe-135.webp` ↔ `inkermanskiy-zmv-winemakers-selection-saperavi-krasnoe-polusladkoe-12.webp` |
| 0.301 | 4 | `019_Золотое Поле/1` | `kaffa-joy-merlot-malbec.webp` ↔ `kaffa-joy-rkatsiteli.webp` |
| 0.302 | 11 | `014_Vibes/1` | `vibes-pinot-grigio-2021.webp` ↔ `vibes-riesling-silvaner-2022.webp` |
| 0.304 | 8 | `028_Olymp Winery/cluster_00_n6` | `olymp-winery-adagum-chardonnay-shardone-beloe-suhoe-11.webp` ↔ `olymp-winery-adagum-saperavi-saperavi-krasnoe-suhoe-11.webp` |
| 0.308 | 10 | `059_Дербент Вино/derbent_vino__cluster_01_n5` | `derbent-vino-di-kaspiko-rkatsiteli-beloe-polusladkoe-11.webp` ↔ `derbent-vino-di-kaspiko-roze-shardone-rozovoe-suhoe-12.webp` |
| 0.309 | 5 | `005_Mancopia/group` | `mancopia-risling.webp` ↔ `mancopia-saperavi.webp` |
| 0.317 | 16 | `092_Мысхако/kaberne__cluster_00_n6` | `vinodelnya-myshako-shardone-avtorskaya-tehnologiya-beloe-suhoe-155.webp` ↔ `vinodelnya-myshako-tempranilo-rozovoe-suhoe-134.webp` |
| 0.321 | 7 | `043_Ведерниковъ/gubernatorskoe__cluster_00_n5` | `vinodelnya-vedernikov-gubernatorskiy-rezerv-krasnoe-kaberne-sovinon-suhoe-14.webp` ↔ `vinodelnya-vedernikov-krasnostop-zolotovskiy-roze-rozovoe-suhoe-12.webp` |
| 0.321 | 7 | `016_Loco Cimbali/2` | `loco-cimbali-oranzh-muskat-belyy-beloe-suhoe-129.webp` ↔ `loco-cimbali-vione-beloe-suhoe-14.webp` |
| 0.324 | 4 | `004_WINEPARK/group` | `winepark-kuchuk-isar-kaberne-sovinon-krasnoe-suhoe-135.webp` ↔ `winepark-pino-blan-beloe-suhoe-125.webp` |
| 0.324 | 10 | `017_Реликта/2` | `relikta-relikta-kaberne-sovinon-krasnoe-suhoe-135.webp` ↔ `relikta-relikta-traminer-beloe-suhoe-11.webp` |
| 0.332 | 9 | `092_Мысхако/other__cluster_02_n5` | `vinodelnya-myshako-merlo-tempranilo-kyuve-krasnoe-polusladkoe-135.webp` ↔ `vinodelnya-myshako-sovinon-semilon-kyuve-sovinon-blan-beloe-suhoe-132.webp` |
| 0.337 | 4 | `004_Cellar Master/group` | `cellar-master-malvaziya-beloe-suhoe-13.webp` ↔ `rebo-rezerv.webp` |
| 0.339 | 3 | `015_Инкерманский ЗМВ/2` | `inkermanskiy-zmv-inkerman-pino-blan-zero-dozazh-beloe-ekstra-bryut-12.webp` ↔ `inkermanskiy-zmv-kokur-belyy-ekstra-bryut-beloe-135.webp` |
| 0.339 | 3 | `039_Alma Valley/6` | `alma-valley-shardone-beloe-suhoe-135.webp` ↔ `alma-valley-shardone-rezerv-beloe-suhoe-135.webp` |
| 0.339 | 2 | `011_Oleg Repin/3` | `oleg-repin-saperavi-carbonica-saperavi-krasnoe-suhoe-13.webp` ↔ `rose-roze-oleg-repin.webp` |
| 0.343 | 8 | `043_Новый Свет. Дом шампанских вин/1` | `novyj-svet-risling-kyuve-de-prestizh.webp` ↔ `novyy-svet-dom-shampanskih-vin-igristoe-vino-vyderzhannoe-polusladkoe-krasnoe-novyy-svet-kaberne-sovinon-12.webp` |
| 0.343 | 3 | `013_Винодельня Жаков/3` | `vinodelnya-zhakov-rozeo-saperavi-rozovoe-suhoe-115.webp` ↔ `vinodelnya-zhakov-saperavi-krasnoe-suhoe-126.webp` |
| 0.346 | 7 | `008_Винодельня Покровская/1` | `vinodelnya-pokrovskaya-ryzhest-rkatsiteli-beloe-suhoe-11.webp` ↔ `vinodelnya-pokrovskaya-sovinon-blan-pokrovskoe-beloe-suhoe-12.webp` |
| 0.346 | 3 | `003_Винодельня Молчанова/group` | `vinodelnya-molchanova-ice-wine-tsvetochnyy-beloe-sladkoe-11.webp` ↔ `vinodelnya-molchanova-krasnostop-zolotovskiy-krasnoe-suhoe-13.webp` |
| 0.349 | 4 | `012_Gunko Winery/1` | `gunko-winery-risling-beloe-suhoe-135.webp` ↔ `gunko-winery-roze-kaberne-fran-rozovoe-suhoe-135.webp` |
| 0.349 | 12 | `019_Винодельня Батрак/2` | `vinodelnya-batrak-perfekt-klassik-pino-nuar-krasnoe-suhoe-12.webp` ↔ `vinodelnya-batrak-prikumskoe-sonnenschein-shardone-beloe-suhoe-12.webp` |
| 0.354 | 8 | `016_Loco Cimbali/1` | `loco-cimbali-loco-cimbali-pinot-meunier-mene-krasnoe-suhoe-125.webp` ↔ `loco-cimbali-merlo-krasnoe-suhoe-138.webp` |
| 0.361 | 6 | `011_Криница/1` | `vinodelnya-krinitsa-azyur-risling-beloe-suhoe-127.webp` ↔ `vinodelnya-krinitsa-sirakyuz-krasnoe-suhoe-13.webp` |
| 0.361 | 3 | `003_VinaBani/group` | `vinabani-pino-nuar-roze-rozovoe-suhoe-12.webp` ↔ `vinabani-saperavi-krasnoe-suhoe-135.webp` |
| 0.362 | 4 | `004_Усадьба Маркотх/group` | `usadba-markoth-kyuve-blan-shardone-beloe-suhoe-12.webp` ↔ `usadba-markoth-merlo-rezerv-krasnoe-suhoe-13.webp` |
| 0.362 | 3 | `043_Ведерниковъ/vedernikov__cluster_01_n4` | `vinodelnya-vedernikov-vedernikov-pet-nat-platovskiy-aligote-bryut-beloe-suhoe-10.webp` ↔ `vinodelnya-vedernikov-vinodelnya-vedernikov-pet-nat-roze-tsimlyanskiy-chernyy-rozovoe-suhoe-12.webp` |
| 0.363 | 6 | `043_Ведерниковъ/tsimlyanskiy_chernyy__cluster_00_n5` | `vinodelnya-vedernikov-tsimlyanskiy-chernyy-blanc-de-noirs-beloe-bryut-117.webp` ↔ `vinodelnya-vedernikov-tsimlyanskiy-chernyy-bryut-roze-rozovoe-14.webp` |
| 0.364 | 11 | `042_Массандра/2` | `massandra-kagor-gurzuf-saperavi-krasnoe-sladkoe-16.webp` ↔ `massandra-muskatel-belyy-belye-sorta-vinograda-beloe-sladkoe-16.webp` |
| 0.365 | 3 | `015_Инкерманский ЗМВ/1` | `inkerman-muskatnoe-beloe.webp` ↔ `inkerman-shato-ruzh.webp` |
| 0.365 | 4 | `031_WINEMAFIA/2` | `barhat.webp` ↔ `riesling.webp` |
| 0.367 | 4 | `022_Усадьба Перовских/cluster_01_n3` | `perovskih_polusladkoe_rosovoe.webp` ↔ `perovskih_polusuhoe_krasnoe.webp` |
| 0.369 | 6 | `006_Dubinin Winery/1` | `dubinin-winery-pino-nuar-bryut-roze-rozovoe-ekstra-bryut-125.webp` ↔ `dubinin-winery-sovinon-blan-beloe-suhoe-12.webp` |
| 0.370 | 3 | `031_WINEMAFIA/1` | `glu-glu-butch.webp` ↔ `glu-glu-samba.webp` |
| 0.373 | 3 | `022_Усадьба Перовских/1` | `perovskih_merlo.webp` ↔ `usadba-perovskih-rkatsiteli-beloe-suhoe-13.webp` |
| 0.375 | 7 | `009_Mantra Estate/2` | `mantra-blanc-de-blancs.webp` ↔ `mantra-estate-sira-roze-rozovoe-suhoe-12.webp` |
| 0.376 | 7 | `100_Фанагория/cluster_03_n7` | `fanagoriya-100-ottenkov-krasnogo-pino-nuar-krasnoe-suhoe-135.webp` ↔ `fanagoriya-101-ottenok-krasnogo-kaberne-kaberne-sovinon-krasnoe-suhoe-14.webp` |
| 0.381 | 11 | `042_Массандра/other__cluster_00_n11` | `pino-gri-avtorskoe.webp` ↔ `roze-avtorskoe-vino.webp` |
| 0.390 | 4 | `021_Denisov Winery/cluster_00_n2` | `denisov-winery-pino-nuar-rozovoe-suhoe-125.webp` ↔ `denisov-winery-risling-beloe-suhoe-115.webp` |
| 0.391 | 3 | `100_Фанагория/cluster_18_n2` | `fanagoriya-sur-lie-clairet-saperavi-krasnoe-suhoe-13.webp` ↔ `fanagoriya-sur-lie-vi-vi-aligote-beloe-suhoe-125.webp` |
| 0.391 | 3 | `031_AGORA WINERY/all__cluster_01_n3` | `agora-rosa-viva-beloe-bryut.webp` ↔ `agora-rosa-viva-rozovoe-polusladkoe.webp` |
| 0.398 | 4 | `100_Фанагория/cluster_05_n6` | `fanagoriya-beloe-polusladkoe.webp` ↔ `fanagoriya-fanagoriya-rose-de-noirs-roze-de-nuar-merlo-igristoe-bryut-rozovoe-11-13.webp` |
| 0.404 | 5 | `100_Фанагория/cluster_06_n5` | `fanagoriya-ice-wine-merlo-rozovoe-sladkoe-10.webp` ↔ `fanagoriya-ice-wine-risling-tihoe-beloe-sladkoe-10.webp` |
| 0.404 | 5 | `011_Oleg Repin/1` | `dry-red-wine-56-rubinovyj-magaracha-oleg-repin.webp` ↔ `oleg-repin-riesling-risling-beloe-suhoe-125.webp` |
| 0.405 | 6 | `023_Раевское/cluster_01_n5` | `vinodelnya-raevskoe-renessans-belyy-blend-risling-beloe-suhoe-121.webp` ↔ `vinodelnya-raevskoe-renessans-rozovoe-tempranilo-suhoe-12.webp` |
| 0.405 | 6 | `026_Chateau de Talu/cluster_02_n5` | `chateau-de-talu-merlot.webp` ↔ `chateau-de-talu-muskat-beloe-suhoe-13.webp` |
| 0.406 | 4 | `010_ЛОРИО -  семейная винодельня Логуновых/1` | `lorio-bryut-belyj.webp` ↔ `lorio-pino-nuar.webp` |
| 0.407 | 2 | `020_Domaine Lipko/2` | `domaine-lipko-kaberne-sovinon-merlo-pomeste-trenzina-krasnoe-suhoe-15.webp` ↔ `domaine-lipko-muskat-pomeste-trenzina-muskat-belyy-beloe-suhoe-119.webp` |
| 0.407 | 5 | `016_Шато АЛВИСА/1` | `cantiani-chardonnay.webp` ↔ `cantiani-rkatsiteli-1.webp` |
| 0.407 | 7 | `008_Шато Ай-Даниль/1` | `shato-ay-danil-bomond-aligote-beloe-suhoe-13.webp` ↔ `shato-ay-danil-skarlatto-da-sole-saperavi-krasnoe-polusladkoe-13.webp` |
| 0.408 | 2 | `009_Табия/3` | `kaberne-sovinon-2.webp` ↔ `oleg.webp` |
| 0.408 | 3 | `048_Шато Пино/3` | `shato-pino-pino-gri-roze-rozovoe-ekstra-bryut-12.webp` ↔ `shato-pino-pino-nuar-roze-rozovoe-ekstra-bryut-115.webp` |
| 0.409 | 3 | `059_Дербент Вино/other__cluster_00_n6` | `igristoe-zhemchuzhnoe-vino-polusladkoe-beloe-di-kaspiko-fiori-di-mare-di-caspico-fiori-di-mare.webp` ↔ `igristoe-zhemchuzhnoe-vino-polusladkoe-rozovoe-di-kaspiko-fiori-di-mare-di-caspico-fiori-di-mare.webp` |
| 0.412 | 2 | `009_Mantra Estate/1` | `magnatum-cuvee-m-blanc-de-blancs.webp` ↔ `magnatum-rose.webp` |
| 0.413 | 3 | `020_Domaine Lipko/4` | `domaine-lipko-pino-nuar-krasnoe-suhoe-12.webp` ↔ `domaine-lipko-syrah-domaine-lipko-sira-krasnoe-suhoe-14.webp` |
| 0.414 | 3 | `059_Дербент Вино/2` | `derbent-vino-endemy-kaberne-fran-krasnoe-suhoe-13.webp` ↔ `derbent-vino-endemy-merlo-krasnoe-suhoe-13.webp` |
| 0.415 | 2 | `096_Кубань-Вино/chateau_tamagne__4` | `chateau-tamagne-nature-orange.webp` ↔ `chateau-tamagne-nature-vert.webp` |
| 0.417 | 3 | `003_Mons Albus/group` | `mons-albus-merlo-rozovoe-suhoe-132.webp` ↔ `mons-albus-rkatsiteli-beloe-suhoe-124.webp` |
| 0.420 | 4 | `092_Мысхако/other__cluster_08_n2` | `vinodelnya-myshako-sesto-senso-tropicheskiy-vzryv-sovinon-blan-beloe-suhoe-12.webp` ↔ `vinodelnya-myshako-sesto-senso-yagodnyy-vzryv-merlo-rozovoe-suhoe-122.webp` |
| 0.421 | 3 | `096_Кубань-Вино/aristov__cluster_03_n3` | `kuban-vino-aristov-amata-byanko-shardone-beloe-suhoe-125.webp` ↔ `kuban-vino-aristov-amata-rosso-kaberne-sovinon-krasnoe-suhoe-145.webp` |
| 0.423 | 4 | `031_AGORA WINERY/1` | `agora-rosa-viva-cabernet-sauvignon-shiraz.webp` ↔ `agora-rosa-viva-muscat.webp` |
| 0.426 | 5 | `033_Союз-Вино/lavetti__cluster_00_n5` | `soyuz-vino-lavetti-beloe-polusladkoe-belye-sorta-vinograda-11.webp` ↔ `soyuz-vino-lavetti-rozovoe-polusladkoe-krasnye-sorta-vinograda-11.webp` |
| 0.428 | 3 | `006_Усадьба Родное Гнездо/2` | `usadba-rodnoe-gnezdo-4-elements-kaberne-sovinon-krasnoe-suhoe-15.webp` ↔ `usadba-rodnoe-gnezdo-4-elements-risling-beloe-polusuhoe-12.webp` |
| 0.428 | 3 | `011_Oleg Repin/2` | `oleg-repin-duvankoy-aligote-aligote-beloe-suhoe-13.webp` ↔ `oleg-repin-listva-cabernet-sauvignon-kaberne-sovinon-krasnoe-suhoe-14.webp` |
| 0.429 | 8 | `016_Агролайн/1` | `agrolayn-mountain-eagle-sauvignon-blanc-sovinon-blan-beloe-suhoe-125.webp` ↔ `agrolayn-mountain-eagle-semillon-semilon-beloe-suhoe-11.webp` |
| 0.430 | 4 | `004_Винодельня 78/group` | `vinodelnya-78-muskat-otbornyy-muskat-yantarnyy-beloe-suhoe-125.webp` ↔ `vinodelnya-78-muskat-polusladkoe-muskat-ottonel-beloe-115.webp` |
| 0.431 | 7 | `019_Золотое Поле/2` | `zolotoe-pole-kaffa-saperavi-krasnoe-suhoe-14.webp` ↔ `zolotoe-pole-kaffa-vione-beloe-suhoe-13.webp` |
| 0.432 | 7 | `100_Фанагория/cluster_04_n7` | `fanagoriya-brule-cuve-brut-rozovoe-merlo-igristoe-bryut-rozovoe-12.webp` ↔ `fanagoriya-brule-muscat-ottonel-brut-muskat-ottonel-beloe-polusladkoe-12.webp` |
| 0.432 | 4 | `043_Ведерниковъ/1` | `vinodelnya-vedernikov-gubernatorskoe-rkatsiteli-beloe-suhoe-13.webp` ↔ `vinodelnya-vedernikov-vedernikov-puhlyakovskiy-beloe-suhoe-12.webp` |
| 0.433 | 8 | `021_Имение Сикоры/cluster_01_n8` | `imenie-sikory-gerts-sikory-kaberne-sovinon-krasnoe-suhoe-14.webp` ↔ `imenie-sikory-semeynoe-nasledie-kaberne-sovinon-krasnoe-suhoe-14.webp` |
| 0.433 | 6 | `043_Новый Свет. Дом шампанских вин/novyy_svet__cluster_00_n8` | `novyy-svet-dom-shampanskih-vin-igristoe-vino-vyderzhannoe-bryut-krasnoe-novyy-svet-kaberne-sovinon-135.webp` ↔ `novyy-svet-dom-shampanskih-vin-rossiyskoe-shampanskoe-vyderzhannoe-polusladkoe-rozovoe-novyy-svet-shardone-125.webp` |
| 0.433 | 2 | `048_Шато Пино/1` | `shato-pino-aligote-rkatsiteli-beloe-suhoe-12.webp` ↔ `shato-pino-kaberne-fran-kaberne-sovinon-krasnoe-suhoe-135.webp` |
| 0.435 | 6 | `028_Olymp Winery/cluster_01_n6` | `olymp-winery-adagum-estate-cabernet-sauvignon-kaberne-sovinon-krasnoe-suhoe-11.webp` ↔ `olymp-winery-adagum-estate-rose-kaberne-sovinon-rozovoe-suhoe-11.webp` |
| 0.436 | 3 | `039_Alma Valley/4` | `alma-valley-merlo-krasnoe-suhoe-13.webp` ↔ `alma-valley-merlo-rezerv-krasnoe-suhoe-14.webp` |
| 0.438 | 6 | `050_Абрау-Дюрсо/victor_dravigny__cluster_00_n6` | `abrau-dyurso-victor-dravigny-bryut.webp` ↔ `abrau-dyurso-victor-dravigny-krasnoe-polusladkoe-kaberne-sovinon-125.webp` |
| 0.440 | 2 | `039_Alma Valley/3` | `alma-valley-pino-nuar-krasnoe-suhoe-13.webp` ↔ `alma-valley-pino-nuar-rezerv-krasnoe-suhoe-14.webp` |
| 0.441 | 2 | `048_Шато Пино/all__cluster_04_n3` | `shato-pino-gravitatsiya-kaberne-sovinon-merlo-krasnoe-suhoe-135.webp` ↔ `shato-pino-shardone-risling-beloe-suhoe-12.webp` |
| 0.443 | 2 | `016_Агролайн/5` | `agrolayn-vexillum-blanc-de-blancs-shardone-beloe-bryut-115.webp` ↔ `agrolayn-vexillum-blanc-de-noirs-pino-nuar-beloe-bryut-12.webp` |
| 0.444 | 2 | `027_Золотая Балка/1` | `cuvee-de-vitmer-brut.webp` ↔ `zolotaya-balka-cuvee-de-vitmer-rose-pino-blan-rozovoe-bryut-12.webp` |
| 0.445 | 12 | `020_Domaine Lipko/1` | `domaine-lipko-blaufrankish-krasnoe-suhoe-126.webp` ↔ `domaine-lipko-white-blend-tsitronnyy-magaracha-beloe-suhoe-115.webp` |
| 0.445 | 2 | `039_Alma Valley/8` | `alma-valley-sovinon-blan-beloe-suhoe-14.webp` ↔ `alma-valley-sovinon-blan-rezerv-beloe-suhoe-14.webp` |
| 0.446 | 9 | `100_Фанагория/cluster_02_n9` | `fanagoriya-dekanter-formula-q-kaberne-sovinon-krasnoe-suhoe-135.webp` ↔ `fanagoriya-dekanter-rkatsiteli-2019-beloe-suhoe-135.webp` |
| 0.448 | 2 | `043_Новый Свет. Дом шампанских вин/0` | `novyj-svet-polusladkoe.webp` ↔ `novyy-svet-dom-shampanskih-vin-novyy-svet-polusladkoe-roze-shardone-rozovoe-115.webp` |
| 0.448 | 2 | `009_Табия/2` | `czitronnyj-magaracha.webp` ↔ `risling-1.webp` |
| 0.449 | 2 | `033_Союз-Вино/other__cluster_00_n5` | `soyuz-vino-kanonicheskie-traditsii-krasnoe-polusladkoe-kaberne-sovinon-115.webp` ↔ `soyuz-vino-kanonicheskie-traditsii-krasnoe-sladkoe-kaberne-sovinon-115.webp` |
| 0.451 | 3 | `059_Дербент Вино/derbent_vino__cluster_05_n2` | `derbent-vino-graf-vorontsov-bryut-beloe-sovinon-blan-105-125.webp` ↔ `derbent-vino-graf-vorontsov-bryut-rozovoe-pervenets-magaracha-105-125.webp` |
| 0.453 | 4 | `043_Ведерниковъ/3` | `vinodelnya-vedernikov-sibirkovyy-beloe-suhoe-11.webp` ↔ `vinodelnya-vedernikov-vedernikov-dolina-dona-krasnoe-suhoe-kaberne-sovinon-125.webp` |
| 0.455 | 3 | `006_Долина Лефкадия/2` | `temelion-blanc-de-blancs.webp` ↔ `temelion-bryut-roze.webp` |
| 0.455 | 2 | `031_WINEMAFIA/3` | `naomi-2022.webp` ↔ `naomi-2023.webp` |
| 0.458 | 4 | `017_Усадьба Дивноморское/3` | `usadba-divnomorskoe-solist-marselan-rozovoe-suhoe-115.webp` ↔ `usadba-divnomorskoe-solnechnyy-veter-shardone-beloe-suhoe-125.webp` |
| 0.458 | 5 | `092_Мысхако/quintessence_new__cluster_00_n8` | `vinodelnya-myshako-quintessence-new-generation-brut-white-shardone-beloe-bryut-11.webp` ↔ `vinodelnya-myshako-quintessence-new-generation-semi-dry-rose-pino-nuar-rozovoe-polusuhoe-11.webp` |
| 0.461 | 2 | `028_Olymp Winery/4` | `olymp-winery-adagum-pinot-noir-pino-nuar-rozovoe-suhoe-11.webp` ↔ `olymp-winery-adagum-sauvignon-sovinon-blan-beloe-suhoe-11.webp` |
| 0.466 | 2 | `039_Alma Valley/5` | `alma-valley-pino-blan-beloe-suhoe-14.webp` ↔ `alma-valley-pino-blan-rezerv-beloe-suhoe-14.webp` |
| 0.469 | 3 | `013_Винодельня Жаков/1` | `vinodelnya-zhakov-saperavi-escape-krasnoe-suhoe-127.webp` ↔ `vinodelnya-zhakov-saperavi-vyderzhannoe-krasnoe-suhoe-115.webp` |
| 0.475 | 5 | `043_Новый Свет. Дом шампанских вин/novyy_svet__cluster_02_n3` | `novyy-svet-dom-shampanskih-vin-novyy-svet-pino-nuar-rozovoe-bryut-13.webp` ↔ `novyy-svet-dom-shampanskih-vin-rossiyskoe-shampanskoe-kollektsionnoe-ekstra-bryut-beloe-novyy-svet-kyuve-risling-125.webp` |
| 0.478 | 2 | `028_Olymp Winery/1` | `olymp-winery-adagum-merlot-merlo-rozovoe-suhoe-10.webp` ↔ `olymp-winery-adagum-pinot-noir-pino-nuar-krasnoe-suhoe-11.webp` |
| 0.486 | 3 | `100_Фанагория/cluster_10_n3` | `fanagoriya-brule-frizzante-brut-beloe-pino-nuar-bryut-115.webp` ↔ `fanagoriya-brule-frizzante-brut-rozovoe-merlo-igristoe-bryut-rozovoe-115.webp` |
| 0.489 | 2 | `010_ЛОРИО -  семейная винодельня Логуновых/2` | `lorio-kaberne-sovinon-i-pino-nuar.webp` ↔ `lorio-sovinon-blan-i-shardone-1.webp` |
| 0.490 | 2 | `012_Gunko Winery/3` | `gunko-winery-blanc-de-blancs-shardone-beloe-bryut-12.webp` ↔ `gunko-winery-bryut-roze-pino-nuar-rozovoe-12.webp` |
| 0.490 | 5 | `059_Дербент Вино/igristoe_vino__cluster_00_n6` | `derbent-vino-di-kaspiko-shardone-beloe-polusladkoe-105-125.webp` ↔ `igristoe-vino-ekstra-bryut-beloe-di-caspico.webp` |
| 0.494 | 2 | `039_Alma Valley/7` | `alma-valley-shiraz-krasnoe-suhoe-13.webp` ↔ `alma-valley-shiraz-sira-rezerv-krasnoe-suhoe-14.webp` |
| 0.494 | 2 | `023_Раевское/1` | `vinodelnya-raevskoe-renessans-beloe-shardone-suhoe-126.webp` ↔ `vinodelnya-raevskoe-renessans-krasnoe-kaberne-sovinon-suhoe-13.webp` |
| 0.499 | 5 | `039_Alma Valley/all__cluster_01_n5` | `alma-valley-solntse-vozduh-vinograd-merlo-krasnoe-polusladkoe-14.webp` ↔ `alma-valley-solntse-vozduh-vinograd-shardone-beloe-polusuhoe-13.webp` |
| 0.500 | 3 | `014_Vibes/2` | `vibes-chardonnay-barrel-fermented-2021.webp` ↔ `vibes-glera-col-fondo-2022.webp` |
| 0.500 | 3 | `096_Кубань-Вино/chateau_tamagne__cluster_07_n2` | `shato-taman-bryut-1.webp` ↔ `shato-taman-bryut.webp` |
| 0.501 | 4 | `004_Усадьба Меркотан/group` | `dnk-kaberne-sovinon.webp` ↔ `dnk-pokolenie.webp` |
| 0.504 | 7 | `008_Два Петра/1` | `twopeters_kaberne_sovinion.webp` ↔ `twopeters_risling.webp` |
| 0.504 | 6 | `050_Абрау-Дюрсо/brut_dor__cluster_00_n6` | `abrau-dyurso-brut-dor-blanc-de-noirs-pino-nuar-beloe-bryut-115.webp` ↔ `abrau-dyurso-brut-dor-rose-pino-nuar-rozovoe-bryut-12.webp` |
| 0.505 | 4 | `009_Литавщук. Litavshchuk vineyards & winery/1` | `roze-premium.webp` ↔ `saperavi-premium.webp` |
| 0.509 | 2 | `016_Шато АЛВИСА/4` | `mont-blanc-blanc-de-blancs.webp` ↔ `mont-blanc-cuvee.webp` |
| 0.510 | 2 | `039_Alma Valley/all__cluster_06_n2` | `alma-valley-locantita-merlot-cabernet-franc.webp` ↔ `locantita-sauvignon-blanc-chardonnay.webp` |
| 0.512 | 3 | `022_Усадьба Перовских/cluster_00_n3` | `perovskih_kaberne_fran_reserve.webp` ↔ `usadba-perovskih-pino-nuar-rezerv-krasnoe-suhoe-122.webp` |
| 0.514 | 2 | `009_Табия/4` | `roze-2.webp` ↔ `rubin-golodrigi.webp` |
| 0.517 | 6 | `025_Château Le Grand Vostock/cluster_02_n6` | `chteau-le-grand-vostock-fagotine-pino-gri-rozovoe-polusladkoe-11.webp` ↔ `chteau-le-grand-vostock-le-chene-royal-reserve-merlo-krasnoe-suhoe-145.webp` |
| 0.520 | 5 | `027_Золотая Балка/cluster_00_n5` | `balaklava-muskat-beloe-polusladkoe.webp` ↔ `wine.webp` |
| 0.522 | 2 | `028_Olymp Winery/2` | `avtorskoe-risling.webp` ↔ `olymp-winery-olimp-avtorskoe-kaberne-sovinon-krasnoe-suhoe-11.webp` |
| 0.525 | 6 | `006_Вина Арпачина/1` | `vina-arpachina-arpachino-inohodets-aligote-beloe-ekstra-bryut-125.webp` ↔ `vina-arpachina-arpachino-tsimlyanskiy-chernyy-rozovoe-ekstra-bryut-13.webp` |
| 0.534 | 2 | `022_Усадьба Перовских/cluster_03_n2` | `perovskih_rose.webp` ↔ `usadba-perovskih-blanc-de-blancs-shardone-beloe-ekstra-bryut-11.webp` |
| 0.534 | 2 | `059_Дербент Вино/4` | `derbent-vino-kavkazian-merlo-krasnoe-polusladkoe-105-125.webp` ↔ `derbent-vino-kavkazian-rkatsiteli-beloe-bryut-105-125.webp` |
| 0.541 | 2 | `013_Винодельня Жаков/4` | `vinodelnya-zhakov-rkatsiteli-eskeyp-krasnoe-suhoe-119.webp` ↔ `vinodelnya-zhakov-shardone-eskeyp-beloe-suhoe-12.webp` |
| 0.544 | 6 | `025_Château Le Grand Vostock/cluster_00_n6` | `chteau-le-grand-vostock-cabernet-sauvignon-kaberne-sovinon-krasnoe-suhoe-14.webp` ↔ `chteau-le-grand-vostock-merlot-reserve-merlo-krasnoe-suhoe-145.webp` |
| 0.547 | 2 | `010_ВайнКрафт/2` | `vaynkraft-pino-nuar-krasnoe-suhoe-13.webp` ↔ `vaynkraft-traminer-traminer-rozovyy-beloe-suhoe-14.webp` |
| 0.549 | 2 | `059_Дербент Вино/0` | `igristoe-vino-bryut-beloe-di-kaspiko-blan-de-blan-di-caspico-blanc-de-blancs.webp` ↔ `igristoe-vino-bryut-rozovoe-di-kaspiko-blan-de-nuar-di-caspico-blanc-de-noirs.webp` |
| 0.551 | 12 | `092_Мысхако/quintessence__cluster_02_n9` | `vinodelnya-myshako-quintessence-storm-shiraz-krasnoe-polusuhoe-15.webp` ↔ `vinodelnya-myshako-quintessence-vione-beloe-suhoe-128.webp` |
| 0.551 | 6 | `042_Массандра/1` | `massandra-kagor-yuzhnoberezhnyy-saperavi-krasnoe-sladkoe-16.webp` ↔ `massandra-lakrima-kristi-aleatiko-krasnoe-sladkoe-16.webp` |
| 0.551 | 2 | `096_Кубань-Вино/chateau_tamagne__3` | `chateau-tamagne-grand-dessert-muscat.webp` ↔ `chateau-tamagne-grand-dessert-nectar.webp` |
| 0.554 | 4 | `033_Союз-Вино/soyuz_vino__cluster_00_n5` | `soyuz-vino-soyuz-vino-kaberne-sovinon-krasnoe-suhoe-12.webp` ↔ `soyuz-vino-soyuz-vino-shardone-suhoe-beloe-11.webp` |
| 0.558 | 3 | `006_Долина Лефкадия/1` | `lefkadiya-beloe.webp` ↔ `roze-malbek.webp` |
| 0.559 | 5 | `050_Абрау-Дюрсо/2` | `abrau-dyurso-russkoe-igristoe-koshernoe-polusladkoe-shardone-beloe-12.webp` ↔ `abrau-dyurso-russkoe-igristoe-polusladkoe-krasnoe-kaberne-sovinon-12.webp` |
| 0.563 | 6 | `026_Усадьба Мезыбь/cluster_01_n6` | `usadba-mezyb-usadba-mezyb-krasnostop-saperavi-krasnoe-suhoe-127.webp` ↔ `usadba-mezyb-usadba-mezyb-shardone-beloe-suhoe-125.webp` |
| 0.570 | 4 | `050_Абрау-Дюрсо/other__cluster_01_n4` | `abrau-dyurso-imperial-brut-rose-pino-nuar-rozovoe-bryut-12.webp` ↔ `abrau-dyurso-imperial-kyuve-pino-nuar-rozovoe-bryut-125.webp` |
| 0.570 | 4 | `016_Виноградники Гай-Кодзора/4` | `gaj-kodzor-sovinon-blan.webp` ↔ `vinogradniki-gay-kodzora-rose-de-gai-kodzor-grenash-rozovoe-suhoe-125.webp` |
| 0.570 | 4 | `096_Кубань-Вино/aristov__cluster_00_n4` | `kuban-vino-aristov-8-byanko-shardone-beloe-suhoe-8.webp` ↔ `kuban-vino-aristov-8-roze-07-merlo-rozovoe-suhoe-8.webp` |
| 0.572 | 2 | `022_Усадьба Перовских/cluster_04_n2` | `shardone-1.webp` ↔ `shardone-rezerv.webp` |
| 0.575 | 5 | `092_Мысхако/other__cluster_05_n3` | `vinodelnya-myshako-kaberne-sovinon-black-out-krasnoe-polusuhoe-16.webp` ↔ `vinodelnya-myshako-risling-blanc-out-beloe-suhoe-145.webp` |
| 0.576 | 8 | `015_KATHARON/1` | `katharon-katharon-kaberne-fran.webp` ↔ `katharon-semi-sweet.webp` |
| 0.577 | 4 | `026_ЗМВ Коктебель/cluster_02_n4` | `zmv-koktebel-pino-gri-desertnoe-beloe-sladkoe-16.webp` ↔ `zmv-koktebel-rkatsiteli-beloe-sladkoe-135.webp` |
| 0.578 | 5 | `010_Andryus Yutsis/1` | `andryus-yutsis-orange-vermentino-beloe-suhoe-112.webp` ↔ `andryus-yutsis-organik-risling-beloe-suhoe-115.webp` |
| 0.584 | 2 | `028_Olymp Winery/3` | `good-steak-cabernet.webp` ↔ `good-steak-merlot.webp` |
| 0.584 | 4 | `026_Усадьба Мезыбь/cluster_02_n4` | `usadba-mezyb-mezyb-kaberne-sovinon-kaberne-fran-vione-rozovoe-suhoe-133.webp` ↔ `usadba-mezyb-mezyb-kaberne-sovinon-krasnoe-suhoe-145.webp` |
| 0.589 | 2 | `096_Кубань-Вино/chateau_tamagne__cluster_06_n2` | `molodoe-shato-taman-1.webp` ↔ `molodoe-shato-taman.webp` |
| 0.589 | 3 | `096_Кубань-Вино/aristov__cluster_02_n3` | `aristov-kyuve-aleksandr-blan-de-nuar.webp` ↔ `aristov-kyuve-aleksandr-roze-de-pino.webp` |
| 0.590 | 4 | `027_AYA Organic Wine & Vineyards/cluster_01_n4` | `toile-de-vin-chardonnay.webp` ↔ `toile-de-vin-pinot-blanc.webp` |
| 0.593 | 4 | `026_ЗМВ Коктебель/cluster_01_n4` | `zmv-koktebel-oranzh-rkatsiteli-beloe-suhoe-125.webp` ↔ `zmv-koktebel-ruzh-rubinovyy-magaracha-krasnoe-suhoe-135.webp` |
| 0.593 | 3 | `007_Cloudy Winery/2` | `cloudy-winery-plohaya-devochka-pryanyy-blend-byanka-beloe-suhoe-125.webp` ↔ `cloudy-winery-plohaya-devochka-sochnyy-pino-noir-pino-nuar-krasnoe-suhoe-12.webp` |
| 0.593 | 3 | `039_Alma Valley/all__cluster_05_n2` | `alma-valley-alma-graviti-pino-nuar-merlo-kaberne-sovinon-krasnoe-suhoe-14.webp` ↔ `alma-valley-graviti-pino-blan-beloe-suhoe-135.webp` |
| 0.593 | 6 | `046_Валерий Захарьин/all__cluster_01_n6` | `valeriy-zaharin-avtohtonnoe-vino-kryma-avtorskiy-kupazh-bastardo-saperavi-kefesiya-bastardo-magarachskiy-krasnoe-suhoe-12.webp` ↔ `valeriy-zaharin-avtorskoe-vino-ot-valeriya-zaharina-krasnoe-pino-nuar-suhoe-125.webp` |
| 0.597 | 2 | `100_Фанагория/12` | `fanagoriya-5-elements-bryut-beloe-pino-gri-igristoe-bryut-beloe-125.webp` ↔ `fanagoriya-5-elements-bryut-rozovoe-saperavi-igristoe-bryut-rozovoe-125.webp` |
| 0.599 | 5 | `016_Виноградники Гай-Кодзора/1` | `vinogradniki-gay-kodzora-semillion-de-gai-kodzor-semilon-beloe-sladkoe-12.webp` ↔ `vinogradniki-gay-kodzora-terroir-red-klyon-de-ga-kodzor-sira-krasnoe-suhoe-14.webp` |
| 0.606 | 3 | `096_Кубань-Вино/aristov__cluster_04_n3` | `kuban-vino-aristov-byanko-shardone-beloe-suhoe-13.webp` ↔ `kuban-vino-aristov-rosso-polusladkoe-saperavi-krasnoe-13.webp` |
| 0.610 | 2 | `100_Фанагория/cluster_15_n2` | `fanagoriya-rose-kaberne-fran-rozovoe-suhoe-13.webp` ↔ `fanagoriya-rose-kaberne-sovinon-rozovoe-polusuhoe-13.webp` |
| 0.615 | 4 | `025_Château Le Grand Vostock/cluster_03_n4` | `chateau-le-grand-vostock-pino-nuar-rezerv-krasnoe-suhoe-14.webp` ↔ `chteau-le-grand-vostock-pinot-noir-reserve-pino-nuar-krasnoe-suhoe-135.webp` |
| 0.616 | 2 | `039_Alma Valley/1` | `alma-valley-kaberne-fran-krasnoe-suhoe-145.webp` ↔ `alma-valley-kaberne-fran-rezerv-krasnoe-suhoe-15.webp` |
| 0.617 | 3 | `096_Кубань-Вино/chateau_tamagne__cluster_03_n3` | `krasnostop-shato-taman.webp` ↔ `risling-shato-taman.webp` |
| 0.621 | 5 | `010_Andryus Yutsis/2` | `andryus-yutsis-shenen-blan-beloe-suhoe-12.webp` ↔ `andryus-yutsis-vione-beloe-suhoe-112.webp` |
| 0.624 | 7 | `096_Кубань-Вино/chateau_tamagne__cluster_01_n7` | `kuban-vino-shato-tamane-rezerv-kaberne-limited-edishn-2022-kaberne-sovinon-krasnoe-suhoe-14.webp` ↔ `kuban-vino-shato-tamane-rezerv-merlo-limited-edishn-2018-krasnoe-suhoe-125.webp` |
| 0.625 | 9 | `100_Фанагория/cluster_01_n9` | `cru-lermont-risling.webp` ↔ `fanagoriya-cru-lermont-cabernet-sauvignon-kaberne-sovinon-krasnoe-suhoe-13.webp` |
| 0.625 | 2 | `031_WINEMAFIA/all__cluster_05_n2` | `tamara-2022.webp` ↔ `tamara.webp` |
| 0.626 | 4 | `043_Новый Свет. Дом шампанских вин/novyy_svet__cluster_03_n3` | `novyy-svet-dom-shampanskih-vin-rossiyskoe-shampanskoe-kollektsionnoe-ekstra-bryut-beloe-novyy-svet-kyuve-de-prestizh-shardone-125.webp` ↔ `novyy-svet-dom-shampanskih-vin-rossiyskoe-shampanskoe-kollektsionnoe-ekstra-bryut-beloe-novyy-svet-risling-kyuve-de-prestizh-125.webp` |
| 0.626 | 6 | `042_Массандра/massandra__cluster_00_n9` | `massandra-portveyn-krasnyy-alushta-krasnye-sorta-vinograda-krasnoe-sladkoe-17.webp` ↔ `portvejn-surozh.webp` |
| 0.628 | 10 | `096_Кубань-Вино/chateau_tamagne__cluster_00_n10` | `shato-taman-kaberne-sovinon.webp` ↔ `shato-taman-krasnostop.webp` |
| 0.631 | 2 | `007_Cloudy Winery/1` | `cloudy-winery-krash-cabernet-sauvignon-kaberne-sovinon-krasnoe-suhoe-14.webp` ↔ `cloudy-winery-krash-super-bryut-shardone-beloe-ekstra-bryut-85.webp` |
| 0.633 | 3 | `006_Усадьба Родное Гнездо/1` | `usadba-rodnoe-gnezdo-4-elements-sira-roze-rozovoe-polusuhoe-135.webp` ↔ `usadba-rodnoe-gnezdo-4-elements-sovinon-blan-beloe-suhoe-12.webp` |
| 0.636 | 7 | `011_Вилла София/2` | `villa-sofiya-kaberne-sovinon-krasnoe-suhoe-133.webp` ↔ `villa-sofiya-trio-roze-pino-nuar-rozovoe-suhoe-14.webp` |
| 0.637 | 3 | `031_WINEMAFIA/all__cluster_00_n3` | `david-2022.webp` ↔ `david.webp` |
| 0.637 | 3 | `027_Золотая Балка/cluster_02_n3` | `rozovoe-polusladkoe-1.webp` ↔ `zolotaya-balka-igristoe-krasnoe-polusladkoe.webp` |
| 0.639 | 2 | `046_Валерий Захарьин/all__cluster_06_n2` | `valeriy-zaharin-albedo-reserve-sary-pandas-beloe-suhoe-115.webp` ↔ `valeriy-zaharin-rubedo-reserve-merlo-krasnoe-suhoe-13.webp` |
| 0.644 | 5 | `052_ESSE/all__cluster_03_n5` | `esse-dolinnoe-cabernet-franc-kaberne-fran-krasnoe-suhoe-13.webp` ↔ `esse-dolinnoe-chrdvnr-shardone-beloe-suhoe-13.webp` |
| 0.647 | 5 | `050_Абрау-Дюрсо/other__cluster_00_n5` | `abrau-dyurso-imperatorskoe-polusladkoe-shardone-beloe-12.webp` ↔ `abrau-dyurso-imperatorskoe-polusuhoe-shardone-beloe-12.webp` |
| 0.647 | 10 | `100_Фанагория/cluster_00_n10` | `fanagoriya-primum-alveus-blanc-de-blancs-2017-shardone-igristoe-bryut-beloe-12.webp` ↔ `fanagoriya-primum-alveus-brut-2021-shardone-beloe-bryut-11-13.webp` |
| 0.647 | 2 | `100_Фанагория/cluster_14_n2` | `fanagoriya-ona-skazala-da-beloe-bryut.webp` ↔ `fanagoriya-ona-skazala-da-beloe-polusladkoe.webp` |
| 0.649 | 3 | `100_Фанагория/cluster_11_n3` | `fanagoriya-fanagoriya-bryut-beloe-sovinon-blan-igristoe-bryut-beloe-11-13.webp` ↔ `fanagoriya-fanagoriya-polusladkoe-rozovoe-sovinon-blan-krasnoe-11-13.webp` |
| 0.666 | 2 | `031_WINEMAFIA/all__cluster_04_n2` | `sacrum-bryut-beloe.webp` ↔ `sacrum-bryut-rozovoe.webp` |
| 0.668 | 2 | `048_Шато Пино/all__cluster_06_n2` | `shato-pino-klassika-sauvignon-blanc.webp` ↔ `shato-pino-pino-gridzhio-beloe-suhoe-12.webp` |
| 0.668 | 3 | `026_ЗМВ Коктебель/cluster_03_n3` | `zmv-koktebel-madera-albilo-beloe-sladkoe-19.webp` ↔ `zmv-koktebel-portveyn-beloe-kreplyonoe-aligote-sladkoe-17.webp` |
| 0.669 | 7 | `092_Мысхако/other__cluster_01_n7` | `vinodelnya-myshako-chernoe-iz-krasnogo-appassimento-kaberne-sovinon-krasnoe-polusuhoe-15.webp` ↔ `vinodelnya-myshako-primitivo-blaufrankish-reserve-krasnoe-suhoe-142.webp` |
| 0.670 | 2 | `021_Имение Сикоры/cluster_02_n2` | `imenie-sikory-krasnostop-zolotovskiy-na-terrasah-rozovoe-suhoe-13.webp` ↔ `imenie-sikory-krasnostop-zolotovskiy-pozdniy-sbor-rozovoe-sladkoe-13.webp` |
| 0.670 | 4 | `042_Массандра/massandra_muskat__cluster_00_n6` | `massandra-muskat-pozdnego-sbora-muskat-belyy-beloe-sladkoe-16.webp` ↔ `massandra-muskat-rozovyy-pozdnego-sbora-rozovoe-sladkoe-10.webp` |
| 0.671 | 9 | `009_Ferrum Winery/1` | `ferrum-winery-kaberne-fran-krasnoe-suhoe-12.webp` ↔ `ferrum-winery-pinot-noir-pino-nuar-rozovoe-suhoe-13.webp` |
| 0.674 | 2 | `022_Усадьба Перовских/cluster_02_n2` | `perovskih_aligote.webp` ↔ `perovskih_odesskiy_chernyi.webp` |
| 0.678 | 5 | `016_Виноградники Гай-Кодзора/3` | `vinogradniki-gay-kodzora-muscat-de-gai-kodzor-sladkiy-muskat-aleksandriyskiy-beloe-sladkoe-14.webp` ↔ `vinogradniki-gay-kodzora-terroir-blanc-de-ga-kodzor-semilon-beloe-suhoe-13.webp` |
| 0.680 | 6 | `031_Golubitskoe Estate/all__cluster_02_n6` | `golubitskoe-estate-shardone-rezerv-beloe-suhoe-135.webp` ↔ `pomeste-golubitskoe-kaberne-sovinon-rezerv-krasnoe-suhoe-143.webp` |
| 0.681 | 2 | `096_Кубань-Вино/chateau_tamagne__cluster_08_n2` | `shato-taman-grape-dance-1.webp` ↔ `shato-taman-grape-dance.webp` |
| 0.681 | 2 | `027_AYA Organic Wine & Vineyards/cluster_06_n2` | `khrustaleva-76-muscat-bryut-beloe.webp` ↔ `khrustaleva-76-muscat-polusladkoe-beloe.webp` |
| 0.683 | 2 | `009_Табия/1` | `bukovinka.webp` ↔ `rozovoe-zoloto.webp` |
| 0.689 | 3 | `046_Валерий Захарьин/all__cluster_02_n4` | `valeriy-zaharin-aleatiko-kefesiya-avtohtonnoe-vino-kryma-ot-valeriya-zaharina-rozovoe-suhoe-125.webp` ↔ `valeriy-zaharin-avtohtonnoe-vino-kryma-ot-valeriya-zaharina-kokur-sary-pandas-kokur-belyy-beloe-suhoe-115.webp` |
| 0.692 | 2 | `039_Alma Valley/2` | `alma-valley-tempranilo-krasnoe-suhoe-13.webp` ↔ `alma-valley-tempranilo-rezerv-krasnoe-suhoe-14.webp` |
| 0.698 | 3 | `092_Мысхако/2` | `vinodelnya-myshako-gevyurtstraminer-kyuve-bryut-beloe-123.webp` ↔ `vinodelnya-myshako-myshako-kyuve-rozovoe-pino-nuar-bryut-123.webp` |
| 0.700 | 2 | `092_Мысхако/other__cluster_07_n2` | `vinodelnya-myshako-rose-de-noirs-pino-nuar-rozovoe-bryut-123.webp` ↔ `vinodelnya-myshako-rouge-de-noirs-merlo-krasnoe-bryut-13.webp` |
| 0.703 | 2 | `043_Новый Свет. Дом шампанских вин/2` | `novyy-svet-dom-shampanskih-vin-igristoe-vino-vyderzhannoe-bryut-rozovoe-novyy-svet-pino-fran-135.webp` ↔ `novyy-svet-dom-shampanskih-vin-igristoe-vino-vyderzhannoe-polusladkoe-rozovoe-novyy-svet-pino-fran-135.webp` |
| 0.704 | 4 | `027_AYA Organic Wine & Vineyards/cluster_00_n4` | `aya-organic-wine-vineyards-blush-2-merlo-rozovoe-ekstra-bryut-135.webp` ↔ `aya-organic-wine-vineyards-blush-4-pino-nuar-krasnoe-ekstra-bryut-129.webp` |
| 0.707 | 2 | `027_AYA Organic Wine & Vineyards/cluster_03_n2` | `aya-khrustaleva-76-merlot-organik.webp` ↔ `khrustaleva-76-merlot-polusuhoe-rozovoe.webp` |
| 0.707 | 3 | `033_Союз-Вино/1` | `soyuz-vino-mosavali-rkatsiteli-beloe-polusladkoe-11.webp` ↔ `soyuz-vino-mosavali-saperavi-polusladkoe-krasnoe-11.webp` |
| 0.717 | 8 | `092_Мысхако/marselan__cluster_00_n5` | `vinodelnya-myshako-zinfandel-mode-krasnoe-suhoe-148.webp` ↔ `vinodelnya-myshako-zinfandel-mode-petnat-rozovoe-polusuhoe-12.webp` |
| 0.724 | 2 | `092_Мысхако/1` | `vinodelnya-myshako-kaberne-myshako-grand-rezerv-kaberne-sovinon-krasnoe-suhoe-125.webp` ↔ `vinodelnya-myshako-shardone-myshako-grand-rezerv-beloe-suhoe-125.webp` |
| 0.727 | 2 | `048_Шато Пино/all__cluster_01_n4` | `shato-pino-exclusive-kaberne-sovinon-shiraz-krasnoe-suhoe-135.webp` ↔ `shato-pino-exclusive-shardone-pino-gri-beloe-suhoe-125.webp` |
| 0.727 | 6 | `026_Усадьба Мезыбь/cluster_00_n6` | `usadba-mezyb-shishka-saperavi-krasnoe-suhoe-13.webp` ↔ `usadba-mezyb-shishka-shenen-blan-sovinon-blan-beloe-suhoe-126.webp` |
| 0.730 | 5 | `005_JD winery/group` | `jd_winery_risling.webp` ↔ `jd_winery_risling_orange.webp` |
| 0.731 | 2 | `046_Валерий Захарьин/1` | `valeriy-zaharin-tangovoe-manto-pino-nuar-krasnoe-suhoe-13.webp` ↔ `valeriy-zaharin-tangovoe-manto-sovinon-sovinon-blan-beloe-suhoe-125.webp` |
| 0.733 | 8 | `008_Два Сердца/1` | `dva-serdtsa-arinarnoa-kaberne-sovinon-krasnoe-suhoe-135.webp` ↔ `dva-serdtsa-vione-beloe-suhoe-125.webp` |
| 0.735 | 2 | `048_Шато Пино/4` | `shato-pino-exclusive-pino-nuar-merlo-krasnoe-suhoe-135.webp` ↔ `shato-pino-exclusive-vione-risling-beloe-suhoe-115.webp` |
| 0.735 | 6 | `052_ESSE/all__cluster_02_n6` | `esse-esse-sira-krasnoe-suhoe-12.webp` ↔ `esse-kaberne-fran-krasnoe-suhoe-13.webp` |
| 0.736 | 2 | `096_Кубань-Вино/1` | `vysokij-bereg-risling-zelenaya-seriya.webp` ↔ `vysokij-bereg-traminer-zelenaya-seriya.webp` |
| 0.737 | 5 | `043_Ведерниковъ/vedernikov__cluster_00_n10` | `vinodelnya-vedernikov-tsimlyanskiy-chernyy-rezerv-krasnoe-suhoe-145.webp` ↔ `vinodelnya-vedernikov-vedernikov-krasnostop-zolotovskiy-krasnoe-suhoe-145.webp` |
| 0.739 | 2 | `100_Фанагория/cluster_20_n2` | `fanagoriya-zelyonoe-vino-risling-tsitronnyy-magaracha-beloe-polusuhoe-11.webp` ↔ `fanagoriya-zelyonoe-vino-risling-tsitronnyy-magaracha-merlo-rozovoe-polusuhoe-11.webp` |
| 0.739 | 2 | `033_Союз-Вино/2` | `soyuz-vino-terra-pia-kaldera-blend-risling-reynskiy-beloe-suhoe-11.webp` ↔ `soyuz-vino-terra-pia-lava-blend-merlo-krasnoe-suhoe-12.webp` |
| 0.742 | 5 | `031_AGORA WINERY/all__cluster_00_n5` | `agora-yachting-merlot.webp` ↔ `agora-yachting-pinot-grigio.webp` |
| 0.743 | 2 | `100_Фанагория/cluster_09_n3` | `fanagoriya-blanc-de-noir-mene-extra-brut-2019-pino-nuar-beloe-ekstra-bryut-12.webp` ↔ `fanagoriya-fanagoriya-blanc-de-noirs-beloe-iz-chyornogo-merlo-igristoe-bryut-beloe-11-13.webp` |
| 0.746 | 5 | `005_Вилла Уркуста/group` | `villa-urkusta-kaberne-sovinon-rezerva-krasnoe-suhoe-15.webp` ↔ `villa-urkusta-kaberne-sovinon-roze-de-sene-rozovoe-suhoe-13.webp` |
| 0.747 | 3 | `006_Донское винодельческое хозяйство -Эльбузд-/3` | `donskoe-vinodelcheskoe-hozyaystvo-elbuzd-risling-beloe-suhoe-12.webp` ↔ `donskoe-vinodelcheskoe-hozyaystvo-elbuzd-shardone-beloe-suhoe-13.webp` |
| 0.750 | 4 | `043_Ведерниковъ/2` | `vinodelnya-vedernikov-krasnostop-zolotovskiy-krasnoe-suhoe-13.webp` ↔ `vinodelnya-vedernikov-pravoberezhnoe-krasnoe-kaberne-sovinon-suhoe-145.webp` |
| 0.751 | 2 | `050_Абрау-Дюрсо/other__cluster_04_n2` | `abrau-dyurso-fizz-beloe-bryut.webp` ↔ `abrau-dyurso-fizz-beloe-polusladkoe.webp` |
| 0.753 | 5 | `028_Olymp Winery/cluster_02_n5` | `olymp-winery-adagum-valley-pinot-noir-pino-nuar-krasnoe-suhoe-11.webp` ↔ `olymp-winery-adagum-valley-rkatsiteli-rkatsiteli-beloe-suhoe-10.webp` |
| 0.754 | 3 | `092_Мысхако/other__cluster_03_n4` | `green-cape-risling.webp` ↔ `myshako-green-cape-shardone-beloe-bryut.webp` |
| 0.756 | 2 | `009_Литавщук. Litavshchuk vineyards & winery/3` | `pozdnij-sbor-beloe.webp` ↔ `pozdnij-sbor-krasnoe.webp` |
| 0.759 | 6 | `035_Собер Баш/all__cluster_01_n6` | `sober-bash-afa-kaberne-sovinon-krasnoe-suhoe-125.webp` ↔ `sober-bash-saperavi-krasnoe-suhoe-13.webp` |
| 0.760 | 2 | `027_AYA Organic Wine & Vineyards/cluster_05_n2` | `evolution-pinot-noir-bryut-rozovoe.webp` ↔ `evolution-pinot-noir.webp` |
| 0.760 | 2 | `031_WINEMAFIA/all__cluster_01_n2` | `amelia-2023.webp` ↔ `amelia.webp` |
| 0.762 | 2 | `031_WINEMAFIA/all__cluster_03_n2` | `daniel-2021.webp` ↔ `daniel-22.webp` |
| 0.762 | 4 | `048_Шато Пино/all__cluster_02_n4` | `shato-pino-pino-nuar-krasnoe-suhoe-135.webp` ↔ `shato-pino-shiraz-krasnoe-suhoe-135.webp` |
| 0.767 | 6 | `033_Союз-Вино/zelyonaya_dolina__cluster_00_n6` | `soyuz-vino-zelyonaya-dolina-kaberne-merlo-kaberne-sovinon-krasnoe-polusladkoe-12.webp` ↔ `soyuz-vino-zelyonaya-dolina-sovinon-blan-polusladkoe-beloe-12.webp` |
| 0.776 | 2 | `029_АРАТТИ/cluster_05_n2` | `belaya-lvicza.webp` ↔ `chernaya-lvicza-polusladkoe-krasnoe.webp` |
| 0.780 | 3 | `023_Раевское/cluster_03_n3` | `vinodelnya-raevskoe-genezis-krasnoe-kaberne-sovinon-suhoe-13.webp` ↔ `vinodelnya-raevskoe-genezis-rozovoe-tempranilo-suhoe-117.webp` |
| 0.783 | 5 | `011_Криница/2` | `vinodelnya-krinitsa-aroma-pti-mansen-beloe-sladkoe-137.webp` ↔ `vinodelnya-krinitsa-rivazh-kaberne-sovinon-krasnoe-suhoe-13.webp` |
| 0.784 | 2 | `026_ЗМВ Коктебель/cluster_04_n2` | `zmv-koktebel-kokur-bryut-beloe-11.webp` ↔ `zmv-koktebel-pino-nuar-bryut-rozovoe-11.webp` |
| 0.787 | 5 | `026_Chateau de Talu/cluster_01_n6` | `chateau-de-talu-kaberne-fran-rezerv-krasnoe-suhoe-13.webp` ↔ `chateau-de-talu-shiraz-rezerv-sira-krasnoe-suhoe-14.webp` |
| 0.788 | 4 | `011_Вилла София/1` | `villa-sofiya-trio-beloe-risling-suhoe-123.webp` ↔ `villa-sofiya-trio-krasnoe-merlo-suhoe-135.webp` |
| 0.789 | 4 | `004_Tempelhof Winery/group` | `tempelhof-winery-risling-risling-reynskiy-beloe-suhoe-115.webp` ↔ `tempelhof-winery-tsimlyanskiy-chernyy-krasnoe-suhoe-125.webp` |
| 0.792 | 2 | `048_Шато Пино/all__cluster_07_n2` | `shato-pino-marselan-merlo-krasnoe-suhoe-13.webp` ↔ `shato-pino-sovinon-blan-semilon-beloe-suhoe-115.webp` |
| 0.793 | 6 | `052_ESSE/all__cluster_01_n6` | `esse-gevyurtstraminer-beloe-suhoe-12.webp` ↔ `esse-sovinon-blan-fyume-beloe-suhoe-128.webp` |
| 0.794 | 3 | `003_Винодельня Бегильдеева/group` | `vinodelnya-begildeeva-kaberne-sovinon-krasnoe-suhoe-14.webp` ↔ `vinodelnya-begildeeva-merlo-krasnoe-suhoe-14.webp` |
