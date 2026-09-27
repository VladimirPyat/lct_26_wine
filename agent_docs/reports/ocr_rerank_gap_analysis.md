# OCR rerank vs top-1 margin — owner_eval 1+2 (51 scored queries)

Offline replay of the production policy (`core.policy.decision.decide`, real PHOCR on YOLO query crops,
`config/ocr_rerank.yaml`). No DB / API. Script: `scripts/simulate_ocr_rerank.py`.
Inputs: `gap_{siglip,dino_p3,dino_p1}_owner_eval_{1,2}_per_query.json` (top-10 + scores, `--crop-queries`).
Full per-query output: `ocr_rerank_sim.json`; OCR lines cache: `ocr_rerank_sim_ocr_cache.json`.

## How prod rerank works

1. Retrieve top-`policy.top_k` (5) by cosine.
2. OCR runs only if `s1 - s2 < policy.margin_min` (0.08).
3. Fuzzy text rerank inside the pool `min(rerank_top=10, top_k=5)` → effectively top-5.
4. `rerank_mode: confident`: the text leader replaces image top-1 only with strong evidence
   (manufacturer+grape or manufacturer+brand) that is distinguishing vs top-1 and not conflicting.
   Color / sweetness words are in `generic_title_tokens` and do not count as evidence.

## Top-1 margin (s1 − s2)

| Model | top-1 correct | median margin (correct) | correct with margin < 0.03 / < 0.08 | margins of wrong top-1 |
|-------|--------------:|------------------------:|------------------------------------:|------------------------|
| SigLIP2 p1e3 | 49/51 | 0.140 | 5 / 13 | 0.037, 0.056 |
| DINO-L P3 | 36/51 | 0.153 | 7 / 12 | 0.000 … 0.064 (15 queries) |
| DINO-L P1 | 37/51 | 0.137 | 9 / 14 | 0.000 … 0.093 (14 queries) |

Correct and wrong answers overlap in margin; a "few hundredths" threshold (0.02–0.03) would catch
0/2 SigLIP errors and only ~half of DINO errors.

## Top-1 after OCR rerank (prod = confident, top_k 5)

| Model | no OCR | margin<0.03 | margin<0.05 | **margin<0.08 (prod)** | always run OCR | `always` mode, <0.08 |
|-------|-------:|------------:|------------:|-----------------------:|---------------:|---------------------:|
| SigLIP2 | 49 | 49 | 49 | **49** | 49 | 45 (breaks 4) |
| DINO-L P3 | 36 | 40 | 41 | **43** | 43 | 45 |
| DINO-L P1 | 37 | 41 | 42 | **44** | 44 | 45 (breaks 1) |

`confident` never broke a correct answer. `always` helps DINO a bit but breaks SigLIP answers.
`top_k=10` never helped.

## SigLIP remaining top-1 misses — both are data issues

- `750a209e.jpg` (set2): photo is **Эндемы Каберне Совиньон розовое сухое**; OCR reads «РОЗОВОЕ СУХОЕ».
  SigLIP top-1 `vino-suhoe-rozovoe-endemy-kaberne-sovinon` is correct; golden
  `derbent-vino-endemy-kaberne-sovinon-krasnoe-suhoe-13` is wrong. The catalog image of that red SKU
  also shows a rosé brut label.
- `35f764ae.jpg` (set1): Alma Valley Chardonnay Reserve 2022. Catalog has the same wine twice
  (`…-135` = 2021 label, `…-14` = 2020 label). Indistinguishable; golden picks one.

## Conclusions

- SigLIP: OCR adds nothing (49→49 at any threshold). With golden/catalog fixed it is effectively 50–51/51.
  Keep `confident`; `margin_min` can drop to 0.05 to save OCR calls (15→8 runs) with no accuracy change.
- DINO: OCR adds +7 top-1 (36→43 for P3) at the current 0.08; lowering the threshold loses fixes.
- Data fixes: golden for `750a209e`, catalog image for `derbent-vino-endemy-kaberne-sovinon-krasnoe-suhoe-13`,
  dedupe Alma Valley Chardonnay Reserve SKUs.
