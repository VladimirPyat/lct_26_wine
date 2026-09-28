# Дообучение энкодера этикеток (embed train)

Краткий отчёт для команды: откуда брались данные, как учили модели, что сработало и что нет. Подробное ТЗ-описание пайплайна — в `docs/dino_train/emb_train.md` (read-only). Детальные метрики и сравнения — в `agent_docs/reports/` (см. таблицу ниже).

## Итог для продакшена

Сейчас в приложении стоит **SigLIP2 so400m** (LoRA, merged в ONNX): `bin/siglip2_wine_p1_epoch_3_fp16.onnx`, препроцесс letterbox 256 — см. [configuration_guide.md](configuration_guide.md). Обучение — **только Phase 1 (symmetric InfoNCE)**, лучший чекпоинт **epoch 3** по Dev-A. На YOLO-кропах запросов (как в API): Dev-A/Dev-B **R@5 = 1.0**, R@1 ≈ 96% (51 запрос) — сводка в `agent_docs/reports/siglip2_embedding_results.md`.

Ранний трек **DINOv2-large + LoRA** (Phase 1 InfoNCE) дал R@5 ≈ 0.85 на Dev-A в Colab; Phase 2 (hard-CE) и Phase 3b (иерархические margin) **не улучшили** baseline — см. `agent_docs/reports/phase3b_stage_FAILED.md`.

---

## DINO vs SigLIP: итоговое сравнение

Условия ниже — **один протокол**, если не оговорено иначе: галерея `dataset/catalog/train` (~2006 YOLO-кропов), запросы owner_eval **после YOLO-кропа** (`queries_crop`), косинус по L2-нормированным эмбеддингам. Dev-A + Dev-B вместе — **51** golden-запрос (27 + 24). Детали: `siglip2_embedding_results.md`, `ocr_rerank_gap_analysis.md`, `compare_dino_large_onnx.md`.

### С чего начинали (малые DINO)

Первые прогоны шли на **компактных DINOv2** (в т.ч. **medium** / base): точность на phone↔catalog была **слишком низкой**, до целевых R@k не дотягивали — поэтому основной линией стали **DINOv2-large** и позже **SigLIP2 so400m**. Малые чекпоинты в прод не рассматривались.

### Без дообучения (foundation «из коробки»)

На задаче «студийный каталог ↔ фото с телефона» **недообученный DINOv2** вёл себя заметно лучше, чем **zero-shot SigLIP2**: у DINO сильнее геометрический pretrain под похожие визуальные паттерны, у SigLIP без FT домен packshot/shelf почти не замыкается (см. `hypothesis_siglip2_vs_dino_backbone.md`). Это **не** аргумент против SigLIP — только против использования VLM без LoRA/InfoNCE.

### После Phase 1 (LoRA + InfoNCE, те же данные и aug)

| Модель | Dev-A (27) R@1 / R@5 | Dev-B (24) R@1 / R@5 | **51 запрос, top-1 (только embed)** |
|--------|----------------------|----------------------|-------------------------------------|
| **SigLIP2 so400m, ep3** | 0.963 / **1.000** | 0.958 / **1.000** | **49/51** |
| DINOv2-**large** phase1 (ONNX, crop) | 0.778 / 0.963 | 0.667 / 0.917 | **37/51** (image top-1) |
| DINOv2-**large** phase3 (ONNX, crop) | 0.778 / 0.963 | 0.625 / 0.958 | **36/51** (image top-1) |
| DINOv2-**large** phase1 (Colab, full-frame eval) | 0.481 / **0.852** best | — | другой протокол (до `queries_crop`) |
| DINOv2-**base** phase2 (crop, letterbox) | 0.741 / 1.000 | 0.625 / 1.000 | слабый **R@1** при высоком R@5 |

Вывод по retrieval: после одинаковой схемы обучения **SigLIP2 сильно лучше по top-1** (отрыв и уверенность shortlist), **R@5 = 100%** на обоих dev-наборах. DINO-large после Phase 1/3 на кропах держит высокий R@5, но **промахи top-1** остаются массовыми (**37/51** и **36/51** без OCR для P1 и P3).

### SigLIP без OCR vs DINO + OCR-реранк

Offline-реплика prod-policy (`margin_min=0.08`, `rerank_mode: confident`, PHOCR + fuzzy на top-5) на тех же 51 запросе — `ocr_rerank_gap_analysis.md`, `siglip_prod_migration_audit.md`:

| Конфигурация | Hit@1 (top-1 slug) |
|--------------|-------------------:|
| **SigLIP2, только эмбеддинги** (`enable_rerank` off) | **49/51** |
| SigLIP2 + OCR **confident** | 49/51 (OCR ничего не чинит и не ломает) |
| DINOv2-L phase3, только эмбеддинги | 36/51 |
| DINOv2-L phase3 + OCR **confident** | **43/51** (+7, без поломок верных) |
| DINOv2-L phase3 + OCR **always** | 45/51 (но mode `always` на SigLIP **ломает** 4 верных ответа) |

Итого: **лучший визуальный энкодер без реранка обгоняет DINO даже с подключённым OCR**. Для SigLIP OCR остаётся запасом на спорные margin и продуктовую политику, а не критичным условием hit@1 на owner_eval.

Два оставшихся «промаха» SigLIP по golden — **ошибки разметки/каталога** (дубль Alma Valley, неверный GT / карточка для Endemy розовое vs красное), а не типичная путаница модели — см. `ocr_rerank_gap_analysis.md`.

---

## Данные на диске

Корень датасета (локальная копия Google Drive `2_embed_train_data`):

| Путь | Назначение |
|------|------------|
| `data/train_dataset/embed_train_data/dataset/catalog/train/` | ~2006 YOLO-кропов каталога — **галерея для retrieval** в ноутбуке и offline-оценке |
| `data/train_dataset/embed_train_data/dataset/catalog/val/` | hold-out каталога для val (если заполнен) |
| `data/train_dataset/embed_train_data/dataset/market/{train,val}/anchor` + `positives/` | **Реальные фото с телефона** (anchor) ↔ **каталожное фото** (positive), собранные вручную / через реверс-поиск |
| `data/train_dataset/embed_train_data/dev_a/`, `dev_b/` | owner_eval set1/set2 — **только eval**, не train |
| `data/train_dataset/embed_train_data/dev_{a,b}/queries_crop/` | те же запросы после прод-YOLO (для честной оценки с API) |
| `data/train_dataset/embed_train_data/near/near_groups.csv` | кластеры «похожих» этикеток (см. раздел про разметку) |
| `data/train_dataset/embed_train_data/_logs/` | JSON/CSV логи Colab (phase1/2/3, retrieval по эпохам) |
| `data/train_dataset/embed_train_data/_models/` | веса на Drive; локально часто пусто, ONNX — в `bin/` |

Важно при синке на Drive: в `dataset/catalog/train` нужны **реальные файлы**, не symlink — иначе на Colab каталог пустой (см. `data/train_dataset/embed_train_data/README.md`).

---

## Ключевые идеи датасета

### 1. Два источника сигнала

1. **Синтетический «телефон ↔ каталог»** — одно и то же каталожное изображение: «чистый» crop (positive) и crop с **phone-style** аугментациями (query). Учит модель узнавать этикетку при съёмке в магазине без подмешивания owner_eval.
2. **Живые пары market** — фото полки/бутылки с телефона сопоставлены с **каталожным** фото того же SKU. Positive часто взят **не из каталога заказчика**, а из открытых источников (реверс-поиск): вин из owner-каталога мало в реальных магазинах, поэтому в обучение шли **произвольные марки**, а мост «поле → студийная этикетка» всё равно учился.

Каталог заказчика при этом:

- целиком попадает в **индекс поиска** (embeddings gallery);
- **train/val split** по каталогу и market — до обучения, seed=42; пары market не режутся между train и val;
- **dev_a / dev_b (owner_eval)** в обучение **не входят** — checklist leakage в `agent_docs/reports/ticket_vec_001_embedding_recall.md`.

### 2. YOLO-кроп и letterbox

Все изображения (каталог и market) — кроп этикетки YOLO (+ padding). Препроцесс обучения: **letterbox** до 224 (DINO) или 256 (SigLIP2), без агрессивного hue — иначе ломается различение «близнецов» по цвету. В проде тот же принцип (см. architecture / configuration_guide).

### 3. Разметка «похожих вин» (near groups)

Вручную собраны кластеры визуально близких этикеток (одна линейка, разные цвета, дубли SKU и т.д.) — дерево `data/train_dataset/near_clusters/`, агрегат `near/near_groups.csv`. Аудит косинусов внутри кластеров: `agent_docs/reports/near_cluster_cosine_audit.md`.

**Зачем это было нужно**, даже когда сложные margin-loss не дали прироста метрик:

- при split train/val **не допускать**, чтобы «близнецы» оказались и в обучении, и в валидации (утечка и завышенные R@k);
- в Phase 2/3 — **маскировать** near из hard-negative / far-margin, чтобы не толкать модель отталкивать legitimately похожие SKU как «чужие» (ошибка Phase 2 — см. handoff).

Разметка окупилась как **гигиена данных и дизайн eval**, а не как обязательный сложный loss.

---

## Методики обучения

| Элемент | DINO v3/v4 | SigLIP v4 (prod) |
|---------|------------|------------------|
| Backbone | DINOv2-large (ранние прогоны — base в `emb_train.md`) | `google/siglip2-so400m-patch16-256` |
| Адаптер | LoRA r=8, α=16 | LoRA на vision `q/k/v/out_proj` |
| Loss (рабочий) | Symmetric **InfoNCE**, τ≈0.07 | То же |
| Батч | 32–64 пары; доля market ~12–15% | 32 = **28 catalog + 4 market** |
| Доп. фазы | Phase 2: hard-pair CE — **хуже** M1 | Phase 3 margin — hinge почти не активен, **метрики без изменений** |
| Выбор модели | Dev-A R@5 в Colab; global best = Phase1 ep8 (DINO-L) | Dev-A, **epoch 3** |

### Сложные margin / hard-negative — что выяснили

По логам `data/train_dataset/embed_train_data/_logs/` (разбор в `phase3b_stage_FAILED.md`):

- **Phase 1 (InfoNCE)** — лучший результат DINO-L: Dev-A R@5 ≈ **0.852**.
- **Phase 2 (hard-CE)** — с первой эпохи ниже M1; `hard_loss` малый, near-twins всё ещё ~26% слотов top-5.
- **Phase 3b (иерархический hinge: near / same-winery / far)** — far-порог почти никогда не срабатывает (`mean_gap_far` ≫ `m_far`); активен в основном near-hinge; R@5 ≈ 0.815, стадия **FAILED**.

Для SigLIP повторили ту же логику: **Phase 1 хватило**; margin-фаза не дала практического выигрыша (`siglip2_embedding_results.md`).

Стратегия Phase 3 (если когда-нибудь перезапускать) зафиксирована в `agent_docs/drafts/dino_train/STRATEGY_PHASE3B_MARGIN.md`; handoff DINO — `HANDOFF_PHASE2_TO_PHASE3.md`.

### Оценка: полный кадр vs YOLO-кроп

Ранние прогоны гоняли Dev-запросы **целиком** (этикетка 20–30% кадра) — метрики занижены, «глубокие» промахи. После `scripts/crop_dev_queries.py` и `queries_crop/` картина совпадает с прод-пайплайном; это критично при сравнении ONNX локально (`scripts/compare_dino_onnx.py`).

---

## Ноутбуки и сборщики (Colab)

Исходники в репозитории (черновики, не `docs/`):

| Файл | Назначение |
|------|------------|
| [`agent_docs/drafts/dino_train/embed_train_v4_siglip.ipynb`](../agent_docs/drafts/dino_train/embed_train_v4_siglip.ipynb) | **Актуальный SigLIP2**: P1 InfoNCE, опциональный auto-P3, экспорт ONNX §8 |
| [`agent_docs/drafts/dino_train/_build_embed_train_v4_siglip.py`](../agent_docs/drafts/dino_train/_build_embed_train_v4_siglip.py) | Регенерация ipynb (SSOT) |
| [`agent_docs/drafts/dino_train/embed_train_v4.ipynb`](../agent_docs/drafts/dino_train/embed_train_v4.ipynb) | DINOv2-large, тот же датасет / батчинг |
| [`agent_docs/drafts/dino_train/embed_train_v3.ipynb`](../agent_docs/drafts/dino_train/embed_train_v3.ipynb) | Архив: Phase 1–3b DINO, индекс `_index/phase*/epoch_*` |
| [`agent_docs/drafts/dino_train/export_onnx_colab.ipynb`](../agent_docs/drafts/dino_train/export_onnx_colab.ipynb) | Минимальный экспорт Drive → ONNX (CPU) |
| [`agent_docs/drafts/dino_train/onnx_fp16_siglip.ipynb`](../agent_docs/drafts/dino_train/onnx_fp16_siglip.ipynb) | fp16-вариант SigLIP ONNX |

**Drive (типичный путь в ноутбуке):** `/content/drive/MyDrive/ЛЦТ26/2_embed_train_data/` — `_models/`, `_logs/`, `_index/`.

Перед Colab: preflight в ноутбуке проверяет market-пары, manifest dev_a/dev_b, наличие `near_groups.csv` (для auto Phase 3).

---

## Отчёты в `agent_docs/reports/` (обучение и embed)

| Отчёт | Содержание |
|-------|------------|
| [`siglip2_embedding_results.md`](../agent_docs/reports/siglip2_embedding_results.md) | Итог SigLIP, R@k на кропах, Phase 1 vs margin |
| [`phase3b_stage_FAILED.md`](../agent_docs/reports/phase3b_stage_FAILED.md) | DINO Phase 1–3b, кривые loss, per-query CSV |
| [`compare_dino_onnx_dev_a.md`](../agent_docs/reports/compare_dino_onnx_dev_a.md) | Локальный ONNX vs Colab logs |
| [`compare_dino_top5_occupants_dev_a.md`](../agent_docs/reports/compare_dino_top5_occupants_dev_a.md) | Кто занимает top-5 (near / intruders) |
| [`compare_dino_confusion_dev_a.md`](../agent_docs/reports/compare_dino_confusion_dev_a.md) | Типы ошибок, путаница виноделен |
| [`near_cluster_cosine_audit.md`](../agent_docs/reports/near_cluster_cosine_audit.md) | QA кластеров near |
| [`ticket_vec_001_embedding_recall.md`](../agent_docs/reports/ticket_vec_001_embedding_recall.md) | Связь recall@5 продa и обучения, anti-leakage |
| [`siglip_prod_migration_audit.md`](../agent_docs/reports/siglip_prod_migration_audit.md) | Переход prod на SigLIP |

Логи обучения (если синкнуты): `phase1_log.json`, `phase2_log.json`, `phase3_attemptA_log.json`, `phase*_epoch*_retrieval.csv` в `_logs/`.

---

## Воспроизведение offline-метрик (без Colab)

```bash
export LD_LIBRARY_PATH="$(pwd)/.venv/lib/python3.12/site-packages/nvidia/cu13/lib:$(pwd)/.venv/lib/python3.12/site-packages/nvidia/cudnn/lib"
D=data/train_dataset/embed_train_data
uv run python scripts/compare_dino_onnx.py --device cuda \
  --onnx bin/siglip2_wine_p1_epoch_3_fp16.onnx \
  --preprocess-json bin/siglip2_wine_p1_epoch_3_preprocess.json \
  --resize letterbox \
  --catalog "$D/dataset/catalog/train" \
  --queries "$D/dev_a/queries_crop" --manifest "$D/dev_a/manifest.tsv" \
  --out-json agent_docs/reports/crop_siglip2_dev_a_check.json
```

Кропы Dev: `uv run python scripts/crop_dev_queries.py` (см. `siglip2_embedding_results.md`).

---

## Связанные мануалы

- Запуск и модели в `bin/` — [quickstart.md](quickstart.md)
- Энкодер, letterbox, переиндексация — [configuration_guide.md](configuration_guide.md)
- YOLO → embed в импорте каталога — [architecture.md](architecture.md)
