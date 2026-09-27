# Compare Phase1 vs Phase2 ONNX (один датасет)

Цель: на **Dev-A** (owner_eval set1, 27 query) сравнить `dinov2_wine_phase1.onnx` и `phase2`, без torch.  
После прогона смотрим R@5 / flips и решаем, идём ли в margin-этап с M1.

## Prefight (уже ок, если файлы на месте)

```bash
cd /work/lct_vine_final
ls -lh bin/dinov2_wine_phase1.onnx bin/dinov2_wine_phase2.onnx
test -f data/train_dataset/embed_train_data/dev_a/manifest.tsv && echo manifest_ok
ls data/train_dataset/embed_train_data/dataset/catalog/train | wc -l   # ~2006
ls data/train_dataset/embed_train_data/dev_a/queries | wc -l           # ~27
```

`near_groups.csv` сейчас может отсутствовать (ты чистишь кластеры) — для первого прогона **не нужен** (false-FAR просто skip).

## Запуск (отдельное окно / tmux)

CPU, ~15–40 мин на оба ONNX (каталог 2k × 2).

```bash
cd /work/lct_vine_final

uv run python scripts/compare_dino_onnx.py \
  --onnx bin/dinov2_wine_phase1.onnx bin/dinov2_wine_phase2.onnx \
  --catalog data/train_dataset/embed_train_data/dataset/catalog/train \
  --queries data/train_dataset/embed_train_data/dev_a/queries \
  --manifest data/train_dataset/embed_train_data/dev_a/manifest.tsv \
  --topk 5 \
  --batch 16 \
  --out-json agent_docs/reports/compare_dino_onnx_dev_a.json
```

Опционально быстрее (больше RAM): `--batch 32`.

Когда пересоберёшь tight-only near:

```bash
# после scripts/scan_near_groups.py → near/near_groups.csv
uv run python scripts/compare_dino_onnx.py \
  --onnx bin/dinov2_wine_phase1.onnx bin/dinov2_wine_phase2.onnx \
  --catalog data/train_dataset/embed_train_data/dataset/catalog/train \
  --queries data/train_dataset/embed_train_data/dev_a/queries \
  --manifest data/train_dataset/embed_train_data/dev_a/manifest.tsv \
  --near-groups data/train_dataset/embed_train_data/near/near_groups.csv \
  --topk 5 \
  --out-json agent_docs/reports/compare_dino_onnx_dev_a.json
```

## Что смотреть в выводе

1. Строки `[dinov2_wine_phase1]` / `[dinov2_wine_phase2]`:
   - `n=` должно быть **27** (или близко)
   - **R@5**, R@1, MRR, `gap12`
2. Блок `flips phase1→phase2`:
   - `LOSE` — query, где Phase2 хуже (главное)
   - `WIN` — где Phase2 лучше
3. Файл: `agent_docs/reports/compare_dino_onnx_dev_a.json`

## Как интерпретировать (для решения по этапу)

| Картина | Вывод |
|---------|--------|
| P1 R@5 ≥ P2, много LOSE | **база = Phase1**; Phase2 hard-CE не брать |
| P2 чуть лучше / паритет | всё равно осторожно; margin стартовать с P1 |
| `n` << 27 или много `gt_missing` | сломан catalog path / имена файлов — стоп, чинить пути |

Ожидание по Colab: P1 ~0.85-ish на мелком Dev, P2 хуже (~0.78). На этом прогоне важны **абсолютные R@5 и flip-лист**, не Colab-цифры 1:1.

## Потом (не в этом окне)

Тот же командой на **dev_b**, когда Dev-A разобрали:

```bash
uv run python scripts/compare_dino_onnx.py \
  --onnx bin/dinov2_wine_phase1.onnx bin/dinov2_wine_phase2.onnx \
  --catalog data/train_dataset/embed_train_data/dataset/catalog/train \
  --queries data/train_dataset/embed_train_data/dev_b/queries \
  --manifest data/train_dataset/embed_train_data/dev_b/manifest.tsv \
  --topk 5 \
  --out-json agent_docs/reports/compare_dino_onnx_dev_b.json
```

Скинь сюда хвост лога (summary + LOSE/WIN) — утвердим margin-этап от M1.

## Логи обучения с Drive (сильно помогают гипотезам)

Локально `_logs/` и `_models/` **пустые** — всё писалось на Colab Drive:

`MyDrive/ЛЦТ26/2_embed_train_data/`

| Артефакт | Зачем агенту |
|----------|----------------|
| `_logs/phase1_log.json` | кривая loss / R@5 по эпохам P1 |
| `_logs/phase2_log.json` | то же + `hard_loss`; видно, с какой эпохи R@5 сел |
| `_logs/phase1_epoch*_retrieval.csv` | per-query rank/top на Dev-A в конце P1 |
| `_logs/phase2_epoch*_retrieval.csv` | то же по эпохам P2 → flip vs P1 **без** нового encode |
| `_models/phase1/best_adapter/training_metadata.json` | epoch, metrics best M1 |
| `_models/phase2/best_adapter/training_metadata.json` | epoch, metrics best M2 |
| `_models/phase*/epoch_N/training_metadata.json` | все промежуточные чекпоинты |

### Скачать к себе (из Drive UI или `rclone`/ручной copy)

В проект:

```text
data/train_dataset/embed_train_data/_logs/          ← все json + csv
data/train_dataset/embed_train_data/_models/phase1/best_adapter/training_metadata.json
data/train_dataset/embed_train_data/_models/phase2/best_adapter/training_metadata.json
```

Минимум для разбора: **`phase1_log.json` + `phase2_log.json` + последний `phase1_epoch*_retrieval.csv` + все `phase2_epoch*_retrieval.csv`**.

### Что сказать агенту в отдельном окне

После `compare_dino_onnx` + скачанных логов:

```text
Сравни ONNX P1/P2 (уже есть agent_docs/reports/compare_dino_onnx_dev_a.json)
и логи data/train_dataset/embed_train_data/_logs/.
Сформулируй: с какой эпохи P2 деградировал R@5, какие query
ухудшились (csv P1 best vs P2), стыкуется ли с flip-листом ONNX,
гипотезы false-FAR / too-hard / weight — без нового обучения.
```
