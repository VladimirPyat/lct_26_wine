# SigLIP2-so400m P1 ep3 — что с чем путается (Dev-A + Dev-B)

**Источник:** `data/train_dataset/embed_train_data/_logs_v4_siglip/phase1_epochepoch_3_{A,B}_retrieval.csv`  
**Карточки промахов:** `siglip2_p1_ep3_devA_misses.md`, `siglip2_p1_ep3_devB_misses.md` (все запросы, где GT не на 1-м месте)  
**Генерация:**

```bash
uv run python scripts/report_dino_miss_top5.py \
  --retrieval-csv data/train_dataset/embed_train_data/_logs_v4_siglip/phase1_epochepoch_3_B_retrieval.csv \
  --near-groups data/train_dataset/embed_train_data/near/near_groups.csv \
  --topk 1 --model-tag siglip2_p1_ep3_devB \
  --out-md agent_docs/reports/siglip2_p1_ep3_devB_misses.md
```

## Итог

| | R@1 | R@5 | GT не на 1-м | промах top-5 |
|---|---|---|---|---|
| Dev-A | 21/27 | 25/27 | 6 | 2 (rank 14, 46) |
| Dev-B | 15/24 | 20/24 | 9 | 4 (rank 8, 22, 26, 44) |

Промахи делятся на две разные группы.

### Группа 1 — «линейка» одной винодельни (rank 2–5, gap −0.005…−0.10)

Бюрнье, Alma Valley, ESSE, Абрау Estates, Ведерниковъ, Chateau de Talu: одинаковый дизайн этикетки, различие — текст (сорт, «Резерв», «Отборное»).  
Соседи в top-5 почти все `near` / `same_winery`, GT почти всегда в top-5.

- Это те самые «похожие», которых меньше 5 — top-5 их вмещает.
- Сдвинуть GT на 1-е место картинкой почти нечем — различие в тексте. Рычаг: **OCR-переранжирование top-5**.
- `35f764ae.jpg`: GT `alma-valley-shardone-rezerv-beloe-suhoe-14.webp`, top-1 `…-135.webp` — **одно и то же вино, два SKU в каталоге** (фактически попадание).

Отдельно 2 случая rank 2 с `other` и крошечным gap (Alma Пино Нуар ↔ «Южный Лес», AGORA Бастардо ↔ Бельбек) — похожие этикетки разных производителей.

### Группа 2 — глубокие промахи (rank 8–46, gap −0.05…−0.14)

Top-5 целиком `other`, часто **другой цвет**: красный Legend of Crimea CS → розовые; красная «Арена» (Сира) → белые/золотистые.  
Это не двойники. Вероятные причины: плохой кроп/блик/ракурс на фото с телефона или нетипичное каталожное фото GT — **проверить картинки глазами**.

**Хабы** — одни и те же каталожные позиции в top-5 у многих запросов (не GT):

| раз в top-5 (51 запрос) | файл |
|--:|---|
| 5 | `leto-kaberne-fran-rezerv-2021-suhoe-krasnoe.webp` (в 4 из 6 глубоких промахов) |
| 3 | `vinodelnya-byurne-krasnostop-krasnoe-suhoe-145.webp` |
| 3 | `esse-merlo-otbornoe-krasnoe-suhoe-13.webp` |

## Выводы для негативов

1. **Catalog↔catalog негативы по near-табличке не достанут группу 2.** В каталожном пространстве LETO и Legend of Crimea и так далеко (`gap_far ≈ 0.51` в Phase3). Путаница возникает только для фото с телефона.
2. Нужны **негативы со стороны запроса**: (фото с телефона из `market/train`, неправильный каталожный top-k текущей модели) → hinge/margin на этих парах. Сейчас `market/train/anchor` = 119 фото.
3. **Нельзя** брать пары из Dev-A/Dev-B как обучающие негативы — это утечка, Dev перестанет быть честной оценкой.
4. Хабы можно проверить без обучения: CSLS / hubness-коррекция на уже готовом индексе (штраф позициям, близким «ко всем»).
5. Группа 1 → OCR-переранжирование top-5, не loss.
