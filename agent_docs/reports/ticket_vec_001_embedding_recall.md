# TICKET-VEC-001 — Поднять vector recall / дискриминацию DINO (owner_eval)

**Status:** OPEN  
**Priority:** high (потолок hit@1)  
**Opened:** 2026-09-24  
**Evidence:** `data/tmp/eval_rank_analysis_recrop_run2/` — set1 после YOLO-каталога: **recall@5 ≈ 85%**, vec@1 ≈ 63%, hit@1 с rerank ≈ 74%.  
**Training notes:** `docs/emb_train.md`

## Почему это потолок

При `policy.top_k=5` **hit@1 ≤ recall@5**. Сейчас recall@5 ≈ **0.85** → hit@1 **>90% недостижим**, пока GT не попадает в top-5 чаще (или не увеличат K / не улучшат эмбеддер). Rerank только переставляет shortlist; он не возвращает GT вне пула.

Pre-recrop (full-frame catalog) было recall@5≈0.67; после crop catalog — заметный рост, но 3–4 кейса всё ещё **gt_not_in_topk**, плюс near-duplicates с малым margin.

## Как учили (кратко из emb_train.md)

- DINOv2-base + LoRA, InfoNCE (T=0.07), batch 64: 87.5% catalog(clean↔phone) + 12.5% market pairs.
- Train pairs **не** из каталога заказчика (внешний gallery) → без leakage в owner test.
- YOLO crop + letterbox 224; phone-style aug (без сильного hue — near-duplicates по цвету).
- На маленьком baseline (10 пар): cosine GT ~0.49–0.83 (mean ~0.60), hard neg ~0.06–0.23, **margin 0.25–0.40**.
- Рекомендация автора: не жёсткий abs threshold; Top-K + gap; gap>0.15 → доверять top1.

На owner_eval set1 сейчас абсолютные top1 scores часто ~0.4–0.55, **gap внутри top5 часто ~0.02–0.05** — сильно слабее «учебного» margin. Гипотеза: домен/индекс (каталог заказчика + полевые query) жёстче baseline; near-SKU конкурируют.

## Гипотезы (по приоритету)

1. **Discriminative margin на реальном каталоге** — малое косинусное «окно» между GT и siblings (та же линейка / цвет). Нужны hard negatives из **каталога** (не из owner_eval test).
2. **Согласованность preprocess** — train: YOLO+padding 5%+letterbox; runtime ONNX: проверить тот же crop/pad/normalize, что при экспорте.
3. **Дообучение LoRA** на hard negatives / harder phone aug, **без** owner_eval set1/set2 как train.
4. **Увеличить retrieval K** (10–20) только для recall-диагностики / rerank pool (latency↑) — не замена улучшению эмбеддинга.
5. **Неразмеченные ~100 фото заказчика** — только после осторожной разметки / weak labels; не мешать с golden owner_eval. Крайний случай — доразметить часть для train, **hold-out** оставить чистым.

## Что не делать без крайней необходимости

- Обучать / fine-tune на `data/owner_eval/1|2` queries (загрязнение метрики сдачи).
- Жёсткий abs cosine cut ~0.5–0.6 как единственный фильтр (прямо против `emb_train.md`).

## Предлагаемые шаги (когда возьмём в работу)

1. Отчёт по miss вне top5 + near-duplicate pairs (slug siblings) на set1/set2 — без изменения модели.
2. Smoke: для hit-кейсов и miss@topk померить cosine(query_crop, catalog_crop_gt) vs best decoy (должны быть как в train: большой gap).
3. План дообучения: hard-negative mining из owner **catalog** (+ optional market), val на hold-out не из eval harness; экспорт ONNX → re-encode catalog.
4. Опционально: `top_k` / HNSW только после (1)–(3).

## Acceptance (позже)

- [ ] recall@5 на set1 ≥ 0.90 **или** документированный потолок + план
- [ ] Средний gap (score_1 − score_gt) на кейсах GT∈top5 вырос vs текущего baseline run2
- [ ] Train/eval leakage checklist пройден (owner_eval queries не в train)

## Links

- Analysis: `data/tmp/eval_rank_analysis_recrop_run2/report.md`
- Train doc: `docs/emb_train.md`
- Related backlog: `TICKET-OPT-001` (batch encode) — ортогонально качеству
