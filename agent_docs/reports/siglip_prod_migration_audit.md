# Переход прода на SigLIP2 + доводка OCR-реранка

Дата: 2026-09-27. Основа: `siglip2_embedding_results.md` (R@1 49/51, R@5 51/51 на кропах),
`ocr_rerank_proposals_siglip.md`.

## 1. Ревизия: что нужно для SigLIP в проде

| # | Где | Сейчас | Нужно |
|---|---|---|---|
| 1 | `config/database.yaml` | `dino_model_path: bin/dinov2_wine_final.onnx` — **файла нет в `bin/`** (прод-конфиг уже сломан), `embedding_dim: 768`, ImageNet mean/std, 224 | `bin/siglip2_wine_p1_epoch_3.onnx`, `embedding_dim: 1152`, `input_size: 256`, mean/std `0.5`, `resize: letterbox`, `pad_fill: [123,116,103]` (значения — `bin/siglip2_wine_p1_epoch_3_preprocess.json`) |
| 2 | `src/core/retrieve/dino_encoder.py` | stretch-resize в квадрат захардкожен; mean/std/size уже из YAML | добавить режим `letterbox` (как при обучении) + цвет паддинга в `DinoPreprocessSettings`; выход `pooler_output` совпадает с экспортом. Имя класса/ключей (`dino_*`) можно обобщить до `encoder_*` отдельным рефакторингом |
| 3 | `alembic/` + `src/db/models.py` | `Vector(768)` берётся из YAML на момент миграции | новая миграция: смена типа колонки `wines.embedding` на `vector(1152)` (данные всё равно пересчитываются). **Деструктивно** — только с подтверждением |
| 4 | Каталог в БД | эмбеддинги DINO | переимпорт: `uv run python -m db.import_catalog --crop-first --recreate-wines` (кропы YOLO как при обучении) |
| 5 | Каталог (данные) | дубли SKU, напр. `alma-valley-shardone-rezerv-beloe-suhoe-135` / `-14` | склеить — это 1 из 2 оставшихся промахов топ-1, OCR его не решит |
| 6 | Ресурсы | модель 1.7 ГБ fp32 | замерить латентность encode на CPU/GPU; ORT CUDA локально требует `LD_LIBRARY_PATH` (см. `siglip2_embedding_results.md`). Опционально fp16-экспорт |
| 7 | `config/ocr_rerank.yaml` policy | `margin_min` 0.1 под DINO | 0.08 (сделано, см. §2); `abs_min: 0.2` перекалибровать под шкалу SigLIP (s1 у верных ≥ 0.67) перед включением not-found gate |
| 8 | Проверка после переимпорта | — | `participant_test.sh` для owner_eval 1/2 через API; ожидание R@1 ≈ 49/51. Сверить топ-5 API с offline `crop_*_per_query.json` (паритет препроцесса) |
| 9 | `tests/` (@Tester) | `test_compute_opt` ссылается на `dinov2_wine_final.onnx`; фикстуры 768 | обновить под SigLIP/1152; тесты на `rerank_mode: confident` |
| 10 | Документация | — | `manuals/configuration_guide.md`, README: модель, препроцесс, откат на DINO (держать DINO-конфиг отдельным YAML) |
| 11 | Ноутбуки | Dev на `queries_crop` (сделано) | препроцесс прода и обучения — оба letterbox (п.2) |

Порядок: 1–2 (код + конфиг) → 3–4 (миграция и переимпорт, с подтверждением) → 8 (eval через API) → 5, 6, 9, 10.

## 2. OCR-реранк: сделано

**Порог:** `policy.margin_min: 0.1 → 0.08` — OCR вызывается реже (SigLIP: 15 вызовов вместо 17 на 51 запрос).

**Новый режим `rerank_mode: confident`** (`src/core/policy/decision.py`). Текстовый лидер заменяет image-топ-1 только если:

1. OCR подтверждает у лидера одну из `strong_combos`: **производитель + сорт** или **производитель + бренд**;
   - производитель — compact-строка или непустой токен производителя (без `винодельня / поместье / estate / шато …`);
   - сорт — все токены одного сорта из `grape_variety` есть в OCR (`пино гри` требует и `пино`, и `гри`);
   - бренд — токены названия, не являющиеся сортом, производителем, цветом/сладостью/«вино» (`generic_title_tokens`), не цифры;
2. среди подтверждённых сортов/бренда есть токен, **которого нет у image-топ-1** (иначе сигнал не различает кандидатов);
3. у image-топ-1 нет своего такого различающего токена (иначе конфликт → оставляем картинку).

Причина пишется в decision log: `rerank_reason` ∈ `text_agrees | weak_text | not_distinguishing | text_conflict | img_drop | strong_text | always`,
плюс `text_leader`, `text_scores`, `evidence` по двум кандидатам. `max_img_drop` — опциональный guard (выключен: без него на Dev лучше и без поломок).
`rerank_mode: always` сохраняет старое поведение (default в `PolicySettings` — для совместимости тестов).

**Оффлайн-проверка** (`scripts/eval_ocr_gate.py`: топ-5 из `crop_score_gaps.json`, PHOCR на `queries_crop`, метаданные из CSV каталога; `ocr_gate_eval*.json`):

| Модель | margin_min | off | always | confident |
|---|---|---|---|---|
| SigLIP2 p1 ep3 | 0.08 | 49/51 | 45/51 (**−4**, 0 исправлено) | **49/51** (0 поломок) |
| DINOv2-L phase3 | 0.08 | 38/51 | 43/51 (+5, 0 поломок) | 42/51 (+4, 0 поломок) |

Вывод: на SigLIP старая безусловная подмена вредит (ломает близнецов: Alma Graviti, Ведерниковъ, Alma Pino Noir → Bakla, Темпранильо → Бюрне),
`confident` безопасен. Два оставшихся промаха SigLIP текстом не решаются: дубль SKU (Alma) и цвет (Endemy розовое vs красное — цвет по запросу
в сильный сигнал не входит).

## Изменённые файлы

`config/ocr_rerank.yaml`, `src/core/config.py` (`rerank_mode`, `strong_combos`, `max_img_drop`, стоп-списки), `src/core/contracts.py`
(`RankedHit.grape_variety`), `src/db/repository.py`, `src/core/text/fuzzy.py` (`label_evidence`), `src/core/policy/decision.py`,
`src/core/policy/logging.py`, `scripts/eval_ocr_gate.py`.

Проверки: `ruff check src/` — OK; `pytest`: политика/OCR/API — 8/8; 11 падений из-за окружения (Postgres auth для `vine`,
нет `bin/dinov2_wine_final.onnx`, устаревший `predictions.jsonl`), не связаны с изменениями.
