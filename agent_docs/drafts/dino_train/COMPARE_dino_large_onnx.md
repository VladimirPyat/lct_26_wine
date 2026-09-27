# Compare DINOv2-**large** Phase1 ONNX (numpy / ORT, без БД)

Offline eval как в Colab: каталог → embeddings → cosine top-k.  
**pgvector / API / `.env` не нужны.** Прод-конфиг (`embedding_dim=768`) не трогать — Large = **1024d**, только этот скрипт.

**Модель:** `bin/dinov2_large_wine_phase1.onnx` (~1.2G, Colab P1 best ep3, Dev-A R@5≈0.889)  
**Скрипт:** `scripts/compare_dino_onnx.py`  
**Логи Colab (torch):** `data/_logs_v4_large/`

---

## Prefight

```bash
cd /work/lct_vine_final

ls -lh bin/dinov2_large_wine_phase1.onnx
test -f data/train_dataset/embed_train_data/dev_a/manifest.tsv && echo ok_a
test -f data/train_dataset/embed_train_data/dev_b/manifest.tsv && echo ok_b
ls data/train_dataset/embed_train_data/dataset/catalog/train | wc -l   # ~2006
ls data/train_dataset/embed_train_data/dev_a/queries | wc -l           # ~27
ls data/train_dataset/embed_train_data/dev_b/queries | wc -l           # ~25
```

---

## Dev-A (n=27)

```bash
cd /work/lct_vine_final

uv run python scripts/compare_dino_onnx.py \
  --onnx bin/dinov2_large_wine_phase1.onnx \
  --catalog data/train_dataset/embed_train_data/dataset/catalog/train \
  --queries data/train_dataset/embed_train_data/dev_a/queries \
  --manifest data/train_dataset/embed_train_data/dev_a/manifest.tsv \
  --topk 5 \
  --batch 8 \
  --out-json agent_docs/reports/compare_dino_large_onnx_dev_a.json \
  2>&1 | tee agent_docs/reports/compare_dino_large_onnx_dev_a.log
```

CPU, Large тяжёлый → `--batch 8` (если RAM ок: `16`). Каталог ~2006 картинок — десятки минут.

---

## Dev-B (n≈24–25)

Индекс каталога **не кэшируется** между запусками — снова полный encode.

```bash
cd /work/lct_vine_final

uv run python scripts/compare_dino_onnx.py \
  --onnx bin/dinov2_large_wine_phase1.onnx \
  --catalog data/train_dataset/embed_train_data/dataset/catalog/train \
  --queries data/train_dataset/embed_train_data/dev_b/queries \
  --manifest data/train_dataset/embed_train_data/dev_b/manifest.tsv \
  --topk 5 \
  --batch 8 \
  --out-json agent_docs/reports/compare_dino_large_onnx_dev_b.json \
  2>&1 | tee agent_docs/reports/compare_dino_large_onnx_dev_b.log
```

---

## Опционально: Large vs base side-by-side (Dev-A)

Два encode каталога — ещё дольше.

```bash
cd /work/lct_vine_final

uv run python scripts/compare_dino_onnx.py \
  --onnx bin/dinov2_large_wine_phase1.onnx bin/dinov2_wine_phase1.onnx \
  --catalog data/train_dataset/embed_train_data/dataset/catalog/train \
  --queries data/train_dataset/embed_train_data/dev_a/queries \
  --manifest data/train_dataset/embed_train_data/dev_a/manifest.tsv \
  --topk 5 \
  --batch 8 \
  --out-json agent_docs/reports/compare_dino_large_vs_base_onnx_dev_a.json \
  2>&1 | tee agent_docs/reports/compare_dino_large_vs_base_onnx_dev_a.log
```

---

## Ожидания (Colab torch SSOT)

| Сет | Colab R@5 | Miss @5 (P1 best) |
|-----|----------:|-------------------|
| Dev-A | **0.889** (24/27) | `2039dd8a`, `7bf0507b`, `bd78e0f6` |
| Dev-B | **0.750** (18/24) | см. `data/_logs_v4_large/phase1_epochbestB_3_retrieval.csv` |

ONNX local может дать чуть другой R@5: preprocess в скрипте = **cv2 square resize**, в Colab = **letterbox**. Смотреть те же miss / flips, не только одну цифру.

---

## Отчёт

После прогона — markdown в `agent_docs/reports/`, например:

- `compare_dino_large_onnx_dev_a.md` / `_dev_b.md`
- ссылки на `.json` / `.log`
- таблица R@1 / R@5 / MRR vs Colab
- список miss и (если делал) flips Large vs base

`near_groups.csv` для первого прогона **не обязателен**.
