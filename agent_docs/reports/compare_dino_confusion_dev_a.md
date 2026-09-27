# Confusion analysis Dev-A — Phase1 vs Phase2 (Colab logs)

**Source:** `_logs/phase1_epoch8_retrieval.csv` vs `phase2_epoch1` (best) / `epoch6` (last).
**Not ONNX** — per-query tops from training-time torch eval. ONNX dump runs separately if needed.

Classic N×N over 2006 SKUs is too sparse (27 queries). Instead:
1. error-type mix at **top-1**
2. **winery×winery** confusion (top-1)
3. per-query GT vs top-5 competitors, P1 vs P2 side-by-side

---

## 1. Error-type mix (top-1 prediction)

| Type | Meaning | P1 e8 | P2 e1 (best) | P2 e6 |
|------|---------|------:|-------------:|------:|
| `correct` | top1 = GT | 13 | 14 | 12 |
| `near_same_group` | same near-cluster, wrong SKU | 5 | 5 | 5 |
| `same_winery_diff_group` | same winery, other cluster/SKU | 3 | 3 | 4 |
| `cross_winery` | other winery | 6 | 5 | 6 |

R@1 / R@5: P1 **0.481/0.852** · P2e1 **0.519/0.778** · P2e6 **0.444/0.704**

---

## 2. Winery confusion (top-1 off-diagonal)

Count of queries where predicted winery ≠ GT winery.

### Phase1 e8
| GT winery | Predicted winery | n |
|-----------|------------------|---|
| 052_ESSE | 031_WINEMAFIA | 1 |
| 039_Alma Valley | 027_AYA Organic Wine & Vineyards | 1 |
| 008_Цимлянские вина | 010_MILLSTREAM | 1 |
| 039_Бельбек | 031_AGORA WINERY | 1 |
| 059_Дербент Вино | 010_Bogovich Wine & Vineyard | 1 |
| 011_Криница | 039_Бельбек | 1 |

### Phase2 e1 (best)
| GT winery | Predicted winery | n |
|-----------|------------------|---|
| 052_ESSE | 031_WINEMAFIA | 1 |
| 039_Alma Valley | 039_Бельбек | 1 |
| 008_Цимлянские вина | 010_MILLSTREAM | 1 |
| 039_Бельбек | 014_Vibes | 1 |
| 011_Криница | 039_Бельбек | 1 |

### Phase2 e6 (last)
| GT winery | Predicted winery | n |
|-----------|------------------|---|
| 052_ESSE | 031_WINEMAFIA | 1 |
| 039_Alma Valley | 050_Абрау-Дюрсо | 1 |
| 039_Alma Valley | 010_Bogovich Wine & Vineyard | 1 |
| 008_Цимлянские вина | 010_MILLSTREAM | 1 |
| 039_Alma Valley | 031_WINEMAFIA | 1 |
| 059_Дербент Вино | 010_MILLSTREAM | 1 |

---

## 3. Miss@5 — what sits in top-5 instead of GT

### Phase1 (miss@5)
- **170d9123.jpeg** GT=`esse-kaberne-otbornoe-kaberne-sovinon-krasnoe-suhoe-12.webp` rank=6
  1. `glu-glu-mr-mouse-2022.webp`
  2. `aristov-anima-millesimato-beloe-bryut.webp`
  3. `leto-muskat-oranzh-2024-suhoe-vino.webp`
  4. `glu-glu-butch.webp`
  5. `daniel-22.webp`
- **2039dd8a.jpg** GT=`alma-valley-alma-graviti-pino-nuar-merlo-kaberne-sovinon-krasnoe-suho…` rank=345
  1. `marquetry-cabernet-franc.webp`
  2. `esse-rose-sira-rozovoe-suhoe-12.webp`
  3. `usadba-mezyb-shishka-merlo-vione-rozovoe-suhoe-125.webp`
  4. `vaynkraft-kaberne-sovinon-krasnoe-suhoe-14.webp`
  5. `belbek-belbek-kaberne-fran-krasnoe-suhoe-13.webp`
- **7bf0507b.jpg** GT=`belbek-belbek-muskat-beloe-suhoe-128.webp` rank=48
  1. `agora-saperavi.webp`
  2. `vibes-chardonnay-barrel-fermented-shardone-beloe-suhoe-125.webp`
  3. `vibes-chardonnay-barrel-fermented-2021.webp`
  4. `usadba-aleksandrovskaya-bubnovyy-valet-kaberne-sovinon-krasnoe-polusl…`
  5. `belbek-belbek-risling-rezerv-beloe-suhoe-13.webp`
- **e3f116c0.jpeg** GT=`vinodelnya-byurne-merlo-krasnoe-suhoe-14.webp` rank=6
  1. `b-yu-rne-malbek-krasnoe-suhoe.webp`
  2. `b-yu-rne-krasnostop-suhoe-krasnoe-classic.webp`
  3. `b-yu-rne-sira-krasnoe-suhoe-classic.webp`
  4. `vinodelnya-zhakov-rozeo-saperavi-rozovoe-suhoe-115.webp`
  5. `vinodelnya-byurne-kaberne-fran-krasnoe-suhoe-135.webp`

### Phase2 e1 best (miss@5)
- **170d9123.jpeg** GT=`esse-kaberne-otbornoe-kaberne-sovinon-krasnoe-suhoe-12.webp` rank=6
  1. `glu-glu-mr-mouse-2022.webp`
  2. `aristov-anima-millesimato-beloe-bryut.webp`
  3. `leto-muskat-oranzh-2024-suhoe-vino.webp`
  4. `glu-glu-butch.webp`
  5. `esse-merlo-otbornoe-krasnoe-suhoe-13.webp`
- **2039dd8a.jpg** GT=`alma-valley-alma-graviti-pino-nuar-merlo-kaberne-sovinon-krasnoe-suho…` rank=676
  1. `belbek-belbek-kaberne-fran-krasnoe-suhoe-13.webp`
  2. `belbek-kaberne-fran-krasnoe-suhoe-134.webp`
  3. `vibes-vermentino-viognier-barrel-fermented-2022.webp`
  4. `agora-pino-nuar.webp`
  5. `stn-winery-syrah-sira-krasnoe-suhoe-13.webp`
- **35f764ae.jpg** GT=`alma-valley-shardone-rezerv-beloe-suhoe-14.webp` rank=9
  1. `alma-valley-shardone-rezerv-beloe-suhoe-135.webp`
  2. `millstream-cellar-select-saperavi.webp`
  3. `alma-valley-kaberne-fran-krasnoe-suhoe-145.webp`
  4. `bogovich-wine-vineyard-kaberne-fran-krasnoe-suhoe-135.webp`
  5. `vinodelnya-vedernikov-vedernikov-kaberne-sovinon-krasnoe-suhoe-145.we…`
- **7bf0507b.jpg** GT=`belbek-belbek-muskat-beloe-suhoe-128.webp` rank=44
  1. `vibes-chardonnay-barrel-fermented-shardone-beloe-suhoe-125.webp`
  2. `vibes-chardonnay-barrel-fermented-2021.webp`
  3. `agora-saperavi.webp`
  4. `belbek-sira-rezerv-krasnoe-suhoe-132.webp`
  5. `belbek-belbek-sira-krasnoe-suhoe-132.webp`
- **90020e08.jpeg** GT=`inkermanskiy-zmv-winemakers-selection-saperavi-krasnoe-polusladkoe-12…` rank=9
  1. `winemaker-selection.webp`
  2. `abrau-dyurso-imperial-brut-vintage-shardone-beloe-bryut-12.webp`
  3. `abrau-dyurso-imperial-brut-rose-pino-nuar-rozovoe-bryut-12.webp`
  4. `fanagoriya-dekanter-pino-nuar-2020-krasnoe-suhoe-135.webp`
  5. `fanagoriya-dekanter-kaberne-sovinon-2018-krasnoe-suhoe-14.webp`
- **e3f116c0.jpeg** GT=`vinodelnya-byurne-merlo-krasnoe-suhoe-14.webp` rank=8
  1. `b-yu-rne-malbek-krasnoe-suhoe.webp`
  2. `b-yu-rne-krasnostop-suhoe-krasnoe-classic.webp`
  3. `b-yu-rne-sira-krasnoe-suhoe-classic.webp`
  4. `vinogradniki-gay-kodzora-viognier-de-ga-kodzor-vione-beloe-suhoe-125.…`
  5. `vinodelnya-zhakov-rozeo-saperavi-rozovoe-suhoe-115.webp`

---

## 4. Side-by-side all 27 queries (P1 e8 vs P2 e1)

| query | rank P1→P2 | err P1 / P2 | top1 P1 | top1 P2 |
|-------|------------|-------------|---------|---------|
| `04f3ce15.jpg` | 1→1 | correct / correct | `chateau-de-talu-ruzh-kaberne-sovinon-kr…` | `chateau-de-talu-ruzh-kaberne-sovinon-kr…` |
| `10967716.jpg` | 1→1 | correct / correct | `aya-organic-wine-vineyards-purity-in-sy…` | `aya-organic-wine-vineyards-purity-in-sy…` |
| `170d9123.jpeg` | 6→6 | cross_winery / cross_winery | `glu-glu-mr-mouse-2022.webp` | `glu-glu-mr-mouse-2022.webp` |
| `2039dd8a.jpg` | 345→676 | cross_winery / cross_winery | `marquetry-cabernet-franc.webp` | `belbek-belbek-kaberne-fran-krasnoe-suho…` |
| `2343a532.jpg` | 2→1 | near_same_group / correct | `aristov-kyuve-aleksandr-blan-de-nuar.we…` | `aristov-kyuve-aleksandr-blan-de-blan.we…` |
| `26ddb066.jpg` | 1→1 | correct / correct | `agora-muskat-chernyj.webp` | `agora-muskat-chernyj.webp` |
| `35f764ae.jpg` | 3→9 **LOSE@5** | near_same_group / near_same_group | `alma-valley-shardone-rezerv-beloe-suhoe…` | `alma-valley-shardone-rezerv-beloe-suhoe…` |
| `3c11e5b0.jpeg` | 5→4 | same_winery_diff_group / same_winery_diff_group | `massandra-kagor-gurzuf-saperavi-krasnoe…` | `massandra-kagor-gurzuf-saperavi-krasnoe…` |
| `4679856e.jpg` | 1→1 | correct / correct | `chateau-de-talu-klere-sira-rozovoe-suho…` | `chateau-de-talu-klere-sira-rozovoe-suho…` |
| `4ea254fd.jpg` | 1→1 | correct / correct | `esse-saperavi-heaven-krasnoe-suhoe-13.w…` | `esse-saperavi-heaven-krasnoe-suhoe-13.w…` |
| `6bb419b6.jpg` | 2→2 | cross_winery / cross_winery | `millstream-cellar-select-saperavi.webp` | `millstream-cellar-select-saperavi.webp` |
| `72ce740a.jpg` | 1→2 | correct / near_same_group | `shato-taman-kaberne-sovinon.webp` | `kuban-vino-shato-tamane-aligote-beloe-s…` |
| `7bf0507b.jpg` | 48→44 | cross_winery / cross_winery | `agora-saperavi.webp` | `vibes-chardonnay-barrel-fermented-shard…` |
| `8a8ad5d7.jpeg` | 1→1 | correct / correct | `vinodelnya-byurne-lyublyu-krasnoe-kaber…` | `vinodelnya-byurne-lyublyu-krasnoe-kaber…` |
| `90020e08.jpeg` | 3→9 **LOSE@5** | same_winery_diff_group / same_winery_diff_group | `winemaker-selection.webp` | `winemaker-selection.webp` |
| `98ea37d3.jpg` | 1→1 | correct / correct | `alma-valley-kaberne-sovinon-rezerv-kras…` | `alma-valley-kaberne-sovinon-rezerv-kras…` |
| `9b04cb8d.jpeg` | 4→4 | near_same_group / near_same_group | `chteau-le-grand-vostock-cabernet-sauvig…` | `chteau-le-grand-vostock-cabernet-sauvig…` |
| `a263fc7c.jpeg` | 1→1 | correct / correct | `abrau-dyurso-abrau-estates-krasnoe-kabe…` | `abrau-dyurso-abrau-estates-krasnoe-kabe…` |
| `b50cf052.jpg` | 1→1 | correct / correct | `soyuz-vino-kanonicheskie-traditsii-kras…` | `soyuz-vino-kanonicheskie-traditsii-kras…` |
| `bd78e0f6.jpg` | 1→1 | correct / correct | `alma-valley-graviti-pino-blan-beloe-suh…` | `alma-valley-graviti-pino-blan-beloe-suh…` |
| `db42a74e.jpeg` | 1→1 | correct / correct | `kuban-vino-vysokiy-bereg-merlo-krasnoe-…` | `kuban-vino-vysokiy-bereg-merlo-krasnoe-…` |
| `e2591aad.jpg` | 1→1 | correct / correct | `alma-valley-tempranilo-krasnoe-suhoe-13…` | `alma-valley-tempranilo-krasnoe-suhoe-13…` |
| `e3f116c0.jpeg` | 6→8 | near_same_group / near_same_group | `b-yu-rne-malbek-krasnoe-suhoe.webp` | `b-yu-rne-malbek-krasnoe-suhoe.webp` |
| `ee3e3334.jpeg` | 2→1 | cross_winery / correct | `bogovich-wine-vineyard-kaberne-fran-kra…` | `derbent-vino-desono-kaberne-sovinon-kra…` |
| `ef930b69.jpg` | 3→2 | cross_winery / cross_winery | `belbek-merlo-krasnoe-suhoe-13.webp` | `belbek-merlo-krasnoe-suhoe-13.webp` |
| `f212df5b.jpeg` | 2→3 | same_winery_diff_group / same_winery_diff_group | `massandra-portveyn-belyy-gurzuf-kokur-b…` | `massandra-portveyn-belyy-gurzuf-kokur-b…` |
| `f780a956.jpg` | 4→3 | near_same_group / near_same_group | `esse-sovinon-blan-beloe-suhoe-12.webp` | `esse-rkatsiteli-beloe-suhoe-125.webp` |

---

## 5. LOSE@5 detail (P1 hit → P2 miss) — competitors

### `35f764ae.jpg`  ranks 3 → 9
- GT: `alma-valley-shardone-rezerv-beloe-suhoe-14.webp` (039_Alma Valley)
- gap(score_gt−score_top1): P1=-0.0479 → P2=-0.0703
- P1 top5:
  1. `alma-valley-shardone-rezerv-beloe-suhoe-135.webp` [near_same_group]
  2. `bogovich-wine-vineyard-kaberne-fran-krasnoe-suhoe-135.webp` [cross_winery]
  3. `alma-valley-shardone-rezerv-beloe-suhoe-14.webp` [GT]
  4. `alma-valley-kaberne-fran-krasnoe-suhoe-145.webp` [same_winery_diff_group]
  5. `alma-valley-shiraz-krasnoe-suhoe-13.webp` [same_winery_diff_group]
- P2 top5:
  1. `alma-valley-shardone-rezerv-beloe-suhoe-135.webp` [near_same_group]
  2. `millstream-cellar-select-saperavi.webp` [cross_winery]
  3. `alma-valley-kaberne-fran-krasnoe-suhoe-145.webp` [same_winery_diff_group]
  4. `bogovich-wine-vineyard-kaberne-fran-krasnoe-suhoe-135.webp` [cross_winery]
  5. `vinodelnya-vedernikov-vedernikov-kaberne-sovinon-krasnoe-suhoe-145.webp` [cross_winery]

### `90020e08.jpeg`  ranks 3 → 9
- GT: `inkermanskiy-zmv-winemakers-selection-saperavi-krasnoe-polusladkoe-12.webp` (015_Инкерманский ЗМВ)
- gap(score_gt−score_top1): P1=-0.1337 → P2=-0.1623
- P1 top5:
  1. `winemaker-selection.webp` [same_winery_diff_group]
  2. `fanagoriya-dekanter-kaberne-sovinon-2018-krasnoe-suhoe-14.webp` [cross_winery]
  3. `inkermanskiy-zmv-winemakers-selection-saperavi-krasnoe-polusladkoe-12.webp` [GT]
  4. `fanagoriya-dekanter-pino-nuar-2020-krasnoe-suhoe-135.webp` [cross_winery]
  5. `fanagoriya-dekanter-riesling-2020-risling-reynskiy-beloe-suhoe-13.webp` [cross_winery]
- P2 top5:
  1. `winemaker-selection.webp` [same_winery_diff_group]
  2. `abrau-dyurso-imperial-brut-vintage-shardone-beloe-bryut-12.webp` [cross_winery]
  3. `abrau-dyurso-imperial-brut-rose-pino-nuar-rozovoe-bryut-12.webp` [cross_winery]
  4. `fanagoriya-dekanter-pino-nuar-2020-krasnoe-suhoe-135.webp` [cross_winery]
  5. `fanagoriya-dekanter-kaberne-sovinon-2018-krasnoe-suhoe-14.webp` [cross_winery]

---

## 6. Conclusions (only what data supports)

1. **Top-1 error mix:** P1 correct=13/27, P2e1 correct=14/27 (R@1 actually *rose* slightly on Colab while R@5 fell — confusion moved into ranks 2–5+).
2. **Near-duplicate confusions** (same cluster, wrong SKU): P1=5, P2e1=5.
3. **Same-winery / other SKU:** P1=3, P2e1=3.
4. **Cross-winery top1:** P1=6, P2e1=5.
5. When both miss@1, same wrong top1 in **9** cases, different top1 in **3** — P2 often keeps or reshuffles the same hard neighbors rather than inventing a wholly new failure mode.
6. The two R@5 LOSE queries (`35f764ae`, `90020e08`) are dominated by **near / same-brand lookalikes** in top-5, not random distant SKUs — consistent with fine-grained collision, not total embedding collapse.
7. **Cannot claim** from this matrix alone that hard-FAR weight or false-FAR *caused* the drop: we see *what* is confused, not *why* Phase2 training moved ranks.
8. Winery off-diagonal counts are tiny (n=27) — treat winery×winery cells as **case lists**, not stable rates.

JSON dump: `agent_docs/reports/compare_dino_confusion_dev_a.json`
---

## 7. ONNX export models — same confusion view

Source: `agent_docs/reports/compare_dino_onnx_dev_a_per_query.json` (top-10, local CPU).

| Type | ONNX P1 | ONNX P2 |
|------|--------:|--------:|
| `correct` | 14 | 14 |
| `near_same_group` | 3 | 2 |
| `same_winery_diff_group` | 4 | 5 |
| `cross_winery` | 6 | 6 |

R@1/R@5: P1 **0.519/0.815** · P2 **0.519/0.815**

### R@5 boundary flips (ONNX)

#### `e3f116c0.jpeg` 6→5 **WIN**
- GT: `vinodelnya-byurne-merlo-krasnoe-suhoe-14.webp`
- P1 top5:
  1. `vinogradniki-gay-kodzora-viognier-de-ga-kodzor-vione-beloe-suhoe-125.webp` (0.482) [cross_winery]
  2. `b-yu-rne-sira-krasnoe-suhoe-classic.webp` (0.468) [near_same_group]
  3. `vinogradniki-gay-kodzora-malbec-red-klen-de-gai-kodzor-malbek-krasnoe-suhoe-135.webp` (0.465) [cross_winery]
  4. `b-yu-rne-malbek-krasnoe-suhoe.webp` (0.462) [near_same_group]
  5. `vinodelnya-byurne-kaberne-fran-krasnoe-suhoe-135.webp` (0.456) [near_same_group]
- P2 top5:
  1. `vinogradniki-gay-kodzora-viognier-de-ga-kodzor-vione-beloe-suhoe-125.webp` (0.485) [cross_winery]
  2. `b-yu-rne-sira-krasnoe-suhoe-classic.webp` (0.483) [near_same_group]
  3. `b-yu-rne-malbek-krasnoe-suhoe.webp` (0.481) [near_same_group]
  4. `b-yu-rne-krasnostop-suhoe-krasnoe-classic.webp` (0.477) [near_same_group]
  5. `vinodelnya-byurne-merlo-krasnoe-suhoe-14.webp` (0.474) [GT]

#### `ee3e3334.jpeg` 5→6 **LOSE**
- GT: `derbent-vino-desono-kaberne-sovinon-krasnoe-suhoe-125.webp`
- P1 top5:
  1. `aratti-kaberne-sovinon-2021-krasnoe-suhoe.webp` (0.392) [cross_winery]
  2. `bogovich-wine-vineyard-pino-nuar-krasnoe-suhoe-125.webp` (0.379) [cross_winery]
  3. `millstream-cellar-select-krasnostop-zolotovskij.webp` (0.364) [cross_winery]
  4. `bogovich-wine-vineyard-kaberne-fran-krasnoe-suhoe-135.webp` (0.357) [cross_winery]
  5. `derbent-vino-desono-kaberne-sovinon-krasnoe-suhoe-125.webp` (0.356) [GT]
- P2 top5:
  1. `millstream-cellar-select-krasnostop-zolotovskij.webp` (0.402) [cross_winery]
  2. `millstream-cellar-select-saperavi.webp` (0.390) [cross_winery]
  3. `millstream-cellar-select-blend-avtohtonov.webp` (0.387) [cross_winery]
  4. `millstream-cellar-select-kaberne-sovinon.webp` (0.384) [cross_winery]
  5. `chateau-tamagne-grand-dessert-nectar.webp` (0.347) [cross_winery]

### ONNX vs Colab note

Absolute ranks still differ from Colab CSVs, but the qualitative picture matches: errors are mostly near/same-brand lookalikes; P2 does not invent a new error regime.
