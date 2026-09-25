# TICKET-RERANK-001 — Адаптировать OCR/fuzzy rerank под DINO shortlist

**Status:** CLOSED  
**Priority:** high (режет hit@1 после хорошего vector)  
**Opened:** 2026-09-24  
**Closed:** 2026-09-25  
**Evidence:** set1 recrop run2 — rerank **helped +5 / hurt −3**; из 7 miss минимум **3** были **vector rank 1**, OCR+fuzzy увёл на sibling slug.  
**Context:** На SIFT-пайплайне тот же fuzzy/OCR rerank работал хорошо; при DINO shortlist расклад другой (уже сильный visual prior, маленькие cosine gaps, много near-duplicates одной марки).

## Наблюдения (set1, enable_rerank=true, phocr)

| Эффект | Count (run2) |
|--------|----------------|
| rerank triggered | 16 / ~27 |
| winner changed | 9 |
| helped (wrong→GT) | 5 |
| **hurt (GT→wrong)** | **3** |

Hurt-примеры (GT был vec#1):

- `alma-valley-alma-graviti-…` → `alma-valley-graviti-kaberne-…` (соседняя SKU)
- `belbek-belbek-muskat-…` → `belbek-muskat-muskat-belyy-…`
- `alma-valley-shardone-rezerv-…` → `alma-valley-shardone-…` (rezerv vs base)

Типичный паттерн: **одна линейка / бренд**, текст OCR общий → fuzzy поднимает «почти то же» сильнее, чем visual #1.

Policy сейчас: `margin_min=0.1`, `abs_min=0.2`, `enable_rerank=true`. При margin < 0.1 почти всегда зовём OCR — а на DINO gaps часто << 0.1 даже когда top1 верный.

Train doc (`docs/emb_train.md`) советовал: если **gap > 0.15** — доверять visual top1 без тяжёлого вмешательства. Наш `margin_min=0.1` ближе, но всё равно часто срабатывает на near-duplicates.

## Гипотезы

1. **Слишком агрессивный trigger** — DINO уже отранжировал; OCR нужен реже / только при малом gap **и** низкой уверенности.
2. **Fuzzy scoring** заточен под SIFT shortlist (слабый visual) и перевешивает DINO score; нет (или слаб) blend `α·dino + β·fuzzy`.
3. **Near-duplicate blindness** — title/manufacturer совпадают; не хватает штрафа за конфликт доп. токенов (rezerv / цвет / год) или бонуса exact slug tokens.
4. **OCR noise** на GPU всё ещё даёт мусорные токены → ложные hit’ы fuzzy.
5. **top_k=5 мало для rerank pool** иногда (GT@4) — но hurt@vec1 важнее.

## Направления фикса (без обучения модели)

1. Калибровка policy: поднять `margin_min` (например 0.12–0.20) или `gap`-gate «не rerank если score_1−score_2 > τ».
2. Hybrid score: не заменять winner на max fuzzy alone; требовать fuzzy Δ выше порога **или** weighted combine с cosine.
3. Near-duplicate rules: сравнивать conflicting tokens (цвет, «резерв», сорт) между OCR lines и candidate fields.
4. A/B на set1/set2: `enable_rerank=false` baseline vs current vs tuned — зафиксировать helped/hurt.
5. Логи: всегда писать `winner_before`, fuzzy scores per candidate, trigger reason (уже частично есть).

## Чего избегать

- Ломать vector path ради rerank.
- Тюнить пороги «в упор» под owner_eval без hold-out / set2 проверки (переобучение политики).

## Resolution (2026-09-25)

Две правки скоринга, пороги YAML не менялись:

1. `exact_title_token_bonus` не даётся, если тот же OCR-токен есть ещё у кого-то в шортлисте (`src/core/text/fuzzy.py`).
2. Глобальный `GENERIC_STOPWORDS` отключён (`src/core/text/normalize.py`). Общие токены гасит shortlist IDF.

Пересчёт на сохранённых OCR и vector shortlist (без нового прогона модели):

| Набор | Было | Стало |
|---|---|---|
| set1 recrop run2 | hit@1 20/27, hurt 3 | hit@1 23/27, hurt 0; три бывших vec#1 вернулись |
| set2 (лог до recrop, 25) | hit@1 18/25, hurt 0 | hit@1 18/25, hurt 0 |

Дальше hit@1 упирается в recall@5: на set2 rerank уже забирает все 6 случаев «GT в top-5, но не #1». Остаток — GT вне пятёрки, это `ticket_vec_001_embedding_recall.md`.

## Acceptance

- [x] На set1: hurt 0, hit@1 23/27 ≥ vec@1
- [x] Set2 не деградирует (18/25 → 18/25)
- [x] Knobs YAML не трогались; изменение в коде, не в `config/ocr_rerank.yaml`

## Links

- `data/tmp/eval_rank_analysis_recrop_run2/report.md`
- `config/ocr_rerank.yaml`, `src/core/policy/`, `src/core/text/fuzzy.py`
- Companion: `ticket_vec_001_embedding_recall.md` (потолок recall@5)
