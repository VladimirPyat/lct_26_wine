# Near-cluster cosine audit (Phase1 ONNX)

- onnx: `bin/dinov2_wine_phase1.onnx`
- root: `/work/lct_vine_final/data/train_dataset/near_clusters`
- threshold: **0.8** (flag if any pair &lt; threshold)
- clusters scanned (≥2 imgs, excl. singletons): **31**
- ok (≥ threshold): **0**
- skipped (&lt;2 imgs): 0
- missing paths: 4
- **flagged: 31**

## Flagged (weakest pair first)

| min cos | n | path | pair |
|--------:|--:|------|------|
| 0.015 | 5 | `005_Винодельня Марко/group` | `vinodelnya-marko-assamblyazh-kaberne-sovinon-krasnoe-suhoe-14.webp` ↔ `vinodelnya-marko-vione-beloe-suhoe-12.webp` |
| 0.051 | 5 | `006_Винодельня Братьев Мельниковых/2` | `kokur-2025.webp` ↔ `vinodelnya-bratev-melnikovyh-kaberne-sovinon-kaberne-fran-dva-brata-krasnoe-suhoe-145.webp` |
| 0.076 | 5 | `012_Gunko Winery/2` | `gunko-winery-monumental-saperavi-krasnoe-suhoe-145.webp` ↔ `gunko-winery-sovinon-blan-gunko-winery-beloe-suhoe-135.webp` |
| 0.132 | 4 | `013_Солнечная долина/1` | `sary-pandas-vyderzhannoe.webp` ↔ `solnechnaya-dolina-chernyy-polkovnik-odesskiy-chernyy-krasnoe-sladkoe-175.webp` |
| 0.164 | 5 | `005_Винодельня Константина Дзитоева/group` | `vinodelnya-konstantina-dzitoeva-kd-bryut-shardone-beloe-115.webp` ↔ `vinodelnya-konstantina-dzitoeva-kion-kaberne-sovinon-krasnoe-suhoe-145.webp` |
| 0.165 | 7 | `050_Абрау-Дюрсо/other__cluster_03_n4` | `abrau-dyurso-pino-nuar-krasnoe-suhoe-125.webp` ↔ `abrau-dyurso-risling-beloe-suhoe-12.webp` |
| 0.169 | 6 | `015_Винодельня Узунов/1` | `vinodelnya-uzunov-aligote-beloe-suhoe-127.webp` ↔ `vinodelnya-uzunov-krasa-kaberne-sovinon-krasnoe-suhoe-125.webp` |
| 0.169 | 5 | `005_Дача Сердюка/group` | `dacha-serdyuka-saperavi-saperavi-severnyy-krasnoe-suhoe-14.webp` ↔ `dacha-serdyuka-sibirkovyy-beloe-suhoe-135.webp` |
| 0.176 | 8 | `015_Винодельня Узунов/3` | `vinodelnya-uzunov-mono-krasnostop-krasnostop-zolotovskiy-krasnoe-suhoe-139.webp` ↔ `vinodelnya-uzunov-rash-risling-beloe-suhoe-127.webp` |
| 0.202 | 11 | `016_LETO/1` | `leto-kaberne-fran-2021-suhoe-krasnoe.webp` ↔ `leto-risling-2024-polusuhoe-vino.webp` |
| 0.204 | 4 | `017_Реликта/1` | `relikta-relikta-dekabrskiy-krasnoe-polusladkoe-125.webp` ↔ `relikta-relikta-pervenets-pervenets-magaracha-beloe-suhoe-12.webp` |
| 0.205 | 6 | `046_Валерий Захарьин/all__cluster_03_n4` | `valeriy-zaharin-bakkal-su-muskat-ottonel-beloe-polusladkoe-115.webp` ↔ `valeriy-zaharin-bakkal-su-saperavi-bastardo-kaberne-sovinon-krasnoe-polusladkoe-11.webp` |
| 0.211 | 5 | `005_Uppa Winery/group` | `uppa-winery-kokur-kokur-belyy-beloe-suhoe-12.webp` ↔ `uppa-winery-pavel-shvets-cabernet-sauvignon-merlot-kaberne-sovinon-krasnoe-suhoe-14.webp` |
| 0.211 | 7 | `008_Цимлянские вина/1` | `czimlyanskoe-bianka.webp` ↔ `kyuve-czimlyanskij-chernyj-i-krasnostop-zolotoj.webp` |
| 0.219 | 3 | `052_ESSE/0` | `esse-prirodno-polusladkoe-krasnoe-merlo-13.webp` ↔ `esse-roze-kaberne-sovinon-rozovoe-suhoe-135.webp` |
| 0.221 | 8 | `019_Золотое Поле/3` | `zolotoe-pole-legend-of-crimea-muscat-ottonel-muskat-ottonel-beloe-suhoe-14.webp` ↔ `zolotoe-pole-legend-of-crimea-red-blend-kaberne-sovinon-krasnoe-suhoe-14.webp` |
| 0.227 | 5 | `019_Скалистый берег/2` | `skalistyy-bereg-pesn-holmov-merlo-krasnoe-suhoe-145.webp` ↔ `skalistyy-bereg-shyopot-tsvetov-risling-beloe-suhoe-109.webp` |
| 0.284 | 7 | `059_Дербент Вино/derbent_vino__cluster_00_n7` | `derbent-vino-desono-saperavi-roze-rozovoe-suhoe-125.webp` ↔ `derbent-vino-desono-shardone-beloe-suhoe-125.webp` |
| 0.306 | 4 | `013_Солнечная долина/2` | `solnechnaya-dolina-meganom-kokur-beloe-bryut.webp` ↔ `solnechnaya-dolina-meganom-kyuve-shardone-beloe-bryut-11.webp` |
| 0.343 | 3 | `052_ESSE/all__cluster_06_n2` | `esse-pino-gri-blush-rozovoe-suhoe-115.webp` ↔ `esse-pino-nuar-krasnoe-suhoe-115.webp` |
| 0.347 | 5 | `011_Domaine de la Vivandiere/1` | `domaine-de-la-vivandiere-malbec-vivandiere-roze-malbek-rozovoe-suhoe-125.webp` ↔ `domaine-de-la-vivandiere-risling-beloe-suhoe-122.webp` |
| 0.366 | 9 | `052_ESSE/all__cluster_00_n10` | `esse-brut-zero-dosage-shardone-beloe-ekstra-bryut-135.webp` ↔ `esse-demi-sec-muscat-nectar-muskat-belyy-beloe-ekstra-bryut-115.webp` |
| 0.430 | 10 | `019_Винодельня Бюрнье/2` | `b-yu-rne-pino-gri-pozdnij-sbor-sladkoe-beloe.webp` ↔ `vinodelnya-byurne-merlo-krasnoe-suhoe-14.webp` |
| 0.432 | 4 | `092_Мысхако/other__cluster_00_n11` | `vinodelnya-myshako-flute-blaufrankish-rozovoe-bryut-126.webp` ↔ `vinodelnya-myshako-flute-bryut-beloe-shardone-11.webp` |
| 0.455 | 10 | `019_Галицкий и Галицкий/1` | `kaberne-sovinon-appasimento.webp` ↔ `risling.webp` |
| 0.511 | 2 | `048_Шато Пино/2` | `koldun-beloe-suhoe.webp` ↔ `shato-pino-koldun-belyy-shardone-beloe-suhoe-12.webp` |
| 0.515 | 2 | `009_Le K2/2` | `le-k2-pino-nuar-pi-krasnoe-suhoe-133.webp` ↔ `le-k2-v-glubine-shardone-beloe-suhoe-13.webp` |
| 0.519 | 5 | `025_Château Le Grand Vostock/cluster_01_n6` | `chteau-le-grand-vostock-chardonnay-reserve-shardone-beloe-suhoe-14.webp` ↔ `chteau-le-grand-vostock-pinot-gris-reserve-pino-gri-beloe-suhoe-135.webp` |
| 0.591 | 3 | `096_Кубань-Вино/aristov__cluster_01_n3` | `aristov-anima-millesimato-beloe-bryut.webp` ↔ `aristov-anima-millesimato.webp` |
| 0.603 | 4 | `046_Валерий Захарьин/all__cluster_04_n4` | `valeriy-zaharin-kaberne-fran-burlyuk-krasnoe-suhoe-13.webp` ↔ `valeriy-zaharin-sandzhoveze-burlyuk-krasnoe-suhoe-13.webp` |
| 0.763 | 3 | `005_GAVRAS/group` | `gavras-levokumskiy-krasnoe-suhoe-12.webp` ↔ `gavras-sira-krasnoe-suhoe-135.webp` |
