# Гипотеза: SigLIP2 / PE вместо (или рядом с) DINOv2 для phone↔catalog retrieval

**Status:** open — parallel to v4 DINOv2-large Colab run (2026-09-26)  
**Priority:** high under time pressure (second backbone bet while Large trains)  
**Related:** `phase3b_stage_FAILED.md`, v4 Large drop-test, earlier SigLIP zero-shot fail (anecdotal)

---

## 0. One-line

На instance-level image→image retrieval современные **vision–language image towers** (SigLIP2-L, Meta PE-L) в бенчмарках сильнее DINOv2-L; наш старый zero-shot провал SigLIP **не опровергает** гипотезу — опровергает только «взять VLM из коробки без FT». Имеет смысл быстрый FT-прогон image-encoder’а тем же Phase1 рецептом.

---

## 1. Уточнение: SigLIP — это не «только text→image»

SigLIP / SigLIP2 — **двухбашенная** модель (image encoder + text encoder), обученная contrastive alignment.

Для нашей задачи нужен **только image tower**:

```
phone_crop  →  get_image_features / vision tower  →  L2  →  cosine vs catalog
catalog_img →  same tower                         →  L2
```

Текст на инференсе **не обязателен**. Text tower можно игнорировать (как в wine/product i2i пайплайнах и в RIS / Elastic SigLIP2 i2i примерах).

Поэтому отказ «это text-to-image, нам не подходит» — **категориальная ошибка**. Подходит ровно тот же протокол, что у DINO: image embedding → top-5.

---

## 2. Что пишут в сильных работах (опора гипотезы)

### 2.1 ILIAS — Instance-Level Image retrieval At Scale (CVPR 2025)

- Сайт: https://vrg.fel.cvut.cz/ilias/  
- Paper: Kordopatis-Zilos et al., CVPR 2025  

На **image→image** instance retrieval при линейной адаптации / сильных global descriptors:

- **SigLIP2-L** и **Perception Encoder (PE-L)** заметно выше **DINOv2-L**  
- Среди non-VLM DINOv2 остаётся одним из лучших  
- Доп. скачок часто даёт local re-ranking — у нас customer хочет top-5 **с эмбеддингов**, поэтому backbone/FT важнее реранка

Интерпретация для нас: «DINO — потолок foundation» **не следует** из литературы 2025; напротив, VLM image towers сейчас лидируют на instance retrieval *в среднем*.

### 2.2 Perception Encoder (Meta, 2025)

- https://arxiv.org/abs/2504.13181  
- PE_core позиционируется как сильные visual embeddings (в т.ч. retrieval); часто сравнивают/ставят рядом или выше SigLIP2 на zero-shot image задачах.  
- Для нас: **plan B/C**, если SigLIP2 FT не взлетит; API/веса проверить под Colab T4 отдельно (размер!).

### 2.3 Индустрия / retail

- Mercari: **fine-tuned SigLIP** image embeddings бьют старый MobileNet на similar-looks (не zero-shot narrative).  
- e8.team retail: **in-domain FT маленькой модели** бьёт гигантские frozen foundation — снова аргумент «нужен FT», не «нужен другой бренд чекпоинта из коробки».

### 2.4 Почему наш zero-shot SigLIP мог быть нулём

Совместимо с литературой и с domain gap catalog↔phone:

| Фактор | Эффект |
|--------|--------|
| Studio packshot ↔ phone shelf | VLM pretrain на web alt-text ≠ ваш bridge |
| Другой preprocess (crop/letterbox) | CLIP/SigLIP чувствительны к resize/crop |
| Оценка «из коробки» без LoRA/InfoNCE | DINO тоже был слабым до FT; выжил после FT |

**Вывод:** zero-shot fail = «этот checkpoint без адаптации не мостит домен», **≠** «SigLIP2 после того же Phase1 бесполезен».

---

## 3. Гипотезы (нумерованный пакет)

### H-S1 — FT SigLIP2 image tower ≥ DINOv2-base M1 на Dev-A R@5 (primary)

После **того же** Phase1 (InfoNCE, YOLO crop, phone_style/market mix, 5–6 ep на T4)  
`SigLIP2` (base или so400m — что влезет в T4) даёт R@5 ≥ **0.852** или хотя бы устойчиво ≥ base@same epoch с лучшим shortlist на borderline.

**Опровержение:** после полного сопоставимого P1 R@5 ≤ DINO-base M1 и те же deep misses (`2039dd8a`, `7bf0507b`).

### H-S2 — Zero-shot VLM ≠ FT VLM (уже частично подтверждено опытом)

Cold-start SigLIP ≈ fail; cold-start DINO ≫ SigLIP; после FT DINO силён.  
Ожидание: FT закрывает часть gap и для SigLIP2.

**Опровержение:** FT SigLIP2 остаётся около zero-shot / не учится (loss не падает / R@5~random).

### H-S3 — Large DINO drop-test и SigLIP FT — ортогональные ставки

- v4 Large: «не падает ли margin на более ёмком DINO»  
- SigLIP2: «не тот ли у нас family backbone»  

Оба можно жечь **параллельно** (Colab Large + второй ноут/другая сессия на SigLIP2-base).

### H-S4 — Если оба не бьют 0.90 R@5 — проблема не в выборе DINO vs SigLIP

Тогда упираемся в данные / fine-grained twins / domain tail (см. H1'/H2' в обсуждении phase3b), а не в «не тот foundation».

---

## 4. Минимальный эксперимент под дедлайн (T4)

Не копировать весь v3/v4. Цель — **сопоставимый Phase1-only**, без Phase2/3.

### 4.1 Кандидаты весов (проверить VRAM до длинного train)

| Приоритет | Checkpoint (HF) | Коммент |
|-----------|-----------------|--------|
| 1 (T4) | `google/siglip2-base-patch16-224` или актуальный **base** SigLIP2 | влезет вероятнее |
| 2 | `google/siglip2-so400m-patch14-384` (если есть / влезает) | сильнее, тяжелее |
| later | PE-L / PE_core | только если SigLIP2 FT обнадёжил или DINO-L провалился |

Точные ID сверить на HF в день запуска (нейминг SigLIP2 обновлялся).

### 4.2 Протокол (один рычаг)

1. **Тот же** preprocess: YOLO crop + letterbox 224 (или native size модели, но тогда A/B честный — зафиксировать один).  
2. LoRA на vision tower (или полный FT последнего блока — что проще в 1 вечер).  
3. Loss: Symmetric InfoNCE, τ=0.07, batch 32 (как v4 T4).  
4. Эпохи: **5–6**, eval Dev-A каждый epoch.  
5. **Не** запускать margin/hard в первом прогоне.  
6. Логи: отдельная папка `_logs_siglip2_p1/`, не мешать `_logs_v4_large/`.

### 4.3 Критерии за 1 вечер

| Исход | Действие |
|-------|----------|
| R@5 ≥ 0.85 (≈23/27) на ≤6 ep | Держать SigLIP2; при необходимости добить ep8 / лёгкий margin |
| R@5 0.74–0.84 и растёт | Добить 2–3 ep; сравнить с DINO-L кривой |
| R@5 ≪ DINO base@same ep и flat | Закрыть H-S1; не тратить PE в этот спринт |

### 4.4 Чего не делать под дедлайн

- Снова zero-shot «для честности» как основной вердикт  
- Смешивать Phase3 margin в первый SigLIP run  
- Менять аугментации и backbone одновременно  
- Ждать ONNX — только Dev-A CSV / torch eval, как в v4

---

## 5. Связь с текущим прогоном DINOv2-large

| Run | Вопрос |
|-----|--------|
| v4 Large P1→P3 | Устойчив ли DINO-family к curriculum drop? |
| SigLIP2 P1-only | Не тот ли backbone family? |

Если Large **не падает** на P3, но потолок ~0.85 — всё равно имеет смысл SigLIP2 как попытка сдвинуть потолок.  
Если Large **падает** как base — H2/forgetting жив; SigLIP2 всё равно полезен как независимая ставка на geometry pretrain.

---

## 6. Практическая памятка для кодера ноутбука

```text
# Псевдо API (transformers)
from transformers import AutoModel, AutoProcessor
# model.get_image_features(**vision_inputs)  # или vision_model + pool
# L2-normalize → InfoNCE как в embed_train_v4
```

- Не кормить text на train/eval для этой гипотезы.  
- `modules_to_save` / LoRA target names у SigLIP **другие**, чем `qkv/proj/fc1/fc2` у DINO — сверить при сборке.  
- Embedding dim ≠ 768/1024 DINO — индекс/ONNX отдельно.

---

## 7. Источники (короткий список)

1. ILIAS — https://vrg.fel.cvut.cz/ilias/ (CVPR 2025)  
2. SigLIP2 docs — https://huggingface.co/docs/transformers/en/model_doc/siglip2 (`get_image_features`)  
3. Perception Encoder — https://arxiv.org/abs/2504.13181  
4. Mercari SigLIP fine-tune (similar looks) — engineering.mercari.com (2024)  
5. Внутреннее: zero-shot SigLIP fail vs DINO FT success; M1 R@5=0.852; phase3b FAILED  

---

## 8. Next action

Пока крутится v4 Large на T4:

1. Поднять **минимальный** Colab: SigLIP2-base + Phase1-only (копия v4 с заменой encoder).  
2. Не блокировать Large; артефакты в отдельных `_models_siglip2_*` / `_logs_siglip2_*`.  
3. После первых 3 ep Large + 3 ep SigLIP — сверка кривых в одном коротком follow-up отчёте.

**Owner decision needed:** стартовать SigLIP2-base FT ноут сейчас (да/нет) и какой HF id фиксируем.
