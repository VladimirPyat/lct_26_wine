# Эмбеддинги: итог по SigLIP2 (задача R@5 ≥ 0.90 выполнена)

Дата: 2026-09-27. Модель: `bin/siglip2_wine_p1_epoch_3.onnx` + `bin/siglip2_wine_p1_epoch_3_preprocess.json`.

## Результат

Оценка offline (ONNX Runtime, CUDA), каталог `dataset/catalog/train` (2006 изображений),
запросы — **YOLO-кропы этикеток** (как в API), препроцесс letterbox 256, mean/std 0.5, L2.

| Набор | n | R@1 | R@5 | MRR |
|---|---:|---:|---:|---:|
| Dev-A (owner_eval 1) | 27 | **0.963** | **1.000** | 0.975 |
| Dev-B (owner_eval 2, held-out) | 24 | **0.958** | **1.000** | 0.979 |

Цель ТЗ R@5 ≥ 0.90 превышена на обоих наборах; топ-1 — 49/51.

Оставшиеся 2 промаха топ-1 (оба внутри топ-5):

| Запрос | Ранг GT | Топ-1 | Причина |
|---|---:|---|---|
| dev_a `35f764ae.jpg` | 3 | `alma-valley-shardone-rezerv-beloe-suhoe-135` | дубль SKU в каталоге (GT `...-14`, то же вино) |
| dev_b `750a209e.jpg` | 2 | `vino-suhoe-rozovoe-endemy-kaberne-sovinon` | серийный близнец: розовое vs красное Endemy Каберне |

## Модель и обучение

- Backbone: `google/siglip2-so400m-patch16-256` (image tower, `get_image_features`, dim 1152).
- LoRA r=8, α=16, targets `q_proj,k_proj,v_proj,out_proj`; merged в ONNX.
- **Только Phase 1**: symmetric InfoNCE (τ=0.07), batch 32 (28 catalog + 4 market), phone-style
  аугментации как в DINO v4; выбран чекпоинт **epoch 3** (по Dev-A).
- Phase 3 (иерархические margin'ы): hinge практически неактивен (active near ≈0.06, far ≈0.001),
  метрики не меняются — **сложные лоссы не понадобились**.
- Ноутбук: `agent_docs/drafts/dino_train/embed_train_v4_siglip.ipynb` (сборщик `_build_embed_train_v4_siglip.py`),
  экспорт ONNX — §8.

## Ключевая находка: оценка на кропах

Ранее Dev-запросы в ноутбуках и в `scripts/compare_dino_onnx.py` подавались **полными фото полки**
(922×2000), тогда как API всегда кропает этикетку YOLO. Этикетка занимала 20–30% кадра → занижение метрик
и «глубокие» промахи (ранг 8–46) с путаницей цвета. На кропах эти промахи исчезли.

Справочно (те же кропы, letterbox): DINOv2-large phase1 — R@5 0.963 / 0.917, R@1 0.815 / 0.667;
DINOv2-base phase2 — R@5 1.000 / 1.000, R@1 0.741 / 0.625. SigLIP2 заметно лучше по R@1 и по отрыву топ-1.

Локальная разница «ноутбук vs скрипт» по DINO объяснялась препроцессом: скрипт растягивал кадр
в квадрат (как прод `DinoOnnxEncoder`), ноутбук — letterbox. На кропах влияние минимально.

## Что изменено в репо

- `scripts/crop_dev_queries.py` — кропы Dev через прод `OnnxYoloCropper` →
  `dev_{a,b}/queries_crop/` + `queries_crop.tsv` (52/52 crop, 0 fallback).
- `scripts/compare_dino_onnx.py` — `--resize stretch|letterbox`, `--preprocess-json`, `--device cuda`,
  кэш каталога учитывает препроцесс.
- Ноутбуки v4 / v4_siglip — `DEV_QUERIES_SUBDIR = "queries_crop"` (на Drive нужны папки `queries_crop`).
- CUDA для ORT локально: `LD_LIBRARY_PATH` на `.venv/.../nvidia/cu13/lib` и `.../nvidia/cudnn/lib`
  (см. `requirements-gpu.txt`).

## Воспроизведение

```bash
export LD_LIBRARY_PATH="$(pwd)/.venv/lib/python3.12/site-packages/nvidia/cu13/lib:$(pwd)/.venv/lib/python3.12/site-packages/nvidia/cudnn/lib"
D=data/train_dataset/embed_train_data
.venv/bin/python scripts/compare_dino_onnx.py --device cuda \
  --onnx bin/siglip2_wine_p1_epoch_3.onnx --preprocess-json bin/siglip2_wine_p1_epoch_3_preprocess.json \
  --catalog $D/dataset/catalog/train --queries $D/dev_a/queries_crop --manifest $D/dev_a/manifest.tsv \
  --catalog-cache agent_docs/reports/cache_siglip2_wine_p1_epoch_3_letterbox.npz \
  --out-json agent_docs/reports/crop_siglip2_wine_p1_epoch_3_dev_a.json
```

Артефакты: `crop_siglip2_wine_p1_epoch_3_dev_{a,b}.json` (+ `_per_query.json`), `crop_score_gaps.json` (скоры топ-5).

## Открытые пункты для интеграции в прод

1. **Энкодер**: прод `DinoOnnxEncoder` захардкожен под DINO (ImageNet mean/std, stretch-resize, dim 768
   в `config/database.yaml`). Для SigLIP нужны: dim 1152, mean/std 0.5, input 256, letterbox
   (как при обучении) — параметризовать энкодер/конфиг, переимпортировать эмбеддинги каталога.
2. **Каталог**: склеить дубли SKU (пример: `alma-valley-shardone-rezerv-beloe-suhoe-135` / `-14`) —
   снимет один из двух оставшихся промахов без OCR.
3. **OCR-реранк**: порог `margin_min=0.1` подобран под DINO; для SigLIP см.
   `ocr_rerank_proposals_siglip.md`.
4. Выборка мала (51 запрос): 1 запрос ≈ 2 п.п. — перед релизом желательно расширить Dev фото с телефона.
