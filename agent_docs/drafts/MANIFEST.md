# MANIFEST — что перенесено в migration/

**Утверждено:** 2026-09-22  
**Целевой стек нового репо:** DINO (ONNX) + PostgreSQL/pgvector + PHOCR + fuzzy OCR-rerank + FastAPI (эндпоинты с нуля).

## KEEP — код (адаптировать импорты в новом пакете)

| Источник | Куда | Примечание |
|----------|------|------------|
| `src/core/ocr/base.py` | `ocr/base.py` | `IOCREngine` |
| `src/core/ocr/phocr.py` | `ocr/phocr.py` | нужен `phocr` + onnxruntime; пути к весам — в `bin/` |
| `src/core/ocr/mock.py` | `ocr/mock.py` | тесты |
| `src/core/ocr/__init__.py` | `ocr/__init__.py` | |
| `src/core/text/fuzzy.py` | `text/fuzzy.py` | зависит от `FuzzySettings` (см. config_samples) |
| `src/core/text/normalize.py` | `text/normalize.py` | транслит, алиасы |
| `src/core/text/ocr_postprocess.py` | `text/ocr_postprocess.py` | |
| `src/core/text/__init__.py` | `text/__init__.py` | |
| `src/core/cropper/onnx_yolo.py` | `cropper/onnx_yolo.py` | тянет `AppSettings` / `compute_threads` / CropResult |
| `src/core/cropper/__init__.py` | `cropper/__init__.py` | |
| `src/core/compute_threads.py` | `support/compute_threads.py` | ORT/OpenCV thread limits |
| `src/core/contracts.py` | `support/contracts_legacy_snippet.py` | полный снимок; для адаптации см. `types_for_adapt.py` |
| — | `support/types_for_adapt.py` | FuzzySettings, WineRecord, CropResult, SearchResult (минимальный набор) |

## KEEP — конфиг (подход + OCR/rerank knobs)

| Файл | Содержание |
|------|------------|
| `config_samples/ocr_rerank.yaml` | hybrid.fuzzy.*, ocr.*, confidence.text.*, hybrid.rerank_top |
| `config_samples/compute_cropper.yaml` | compute.device cpu\|cuda, cropper.*, yolo path |
| `config_samples/README.md` | как склеить с новыми порогами DINO |

Пороги DINO (`margin`, `abs_min`, enable_rerank, enable_not_found) — **не** из старого YAML; задаются в новом проекте.

## KEEP — бинарники / модели

| Файл | Роль |
|------|------|
| `bin/yolo_detect_labels.onnx` | запасной YOLO |
| `bin/yolo_detect_labels_2.onnx` | актуальный (был в `app.yaml`) |

**Не кладём в migration:**

- DINO ONNX → сразу в новый репо `bin/`
- веса PHOCR → после установки `phocr` в новом venv (перенос из site-packages при необходимости offline)

Инференс целевой: **onnxruntime** (± CUDA EP). `torch` / `transformers` в runtime нового сервиса не планируем.

## KEEP — eval заказчика

| Источник | Куда |
|----------|------|
| `docs/main_eval/participant_test.sh` | `eval_organizer/participant_test.sh` |
| `docs/main_eval/README.md` | `eval_organizer/README.md` |
| `data/test_dataset/owner_eval/**` | `data/owner_eval/**` (наборы 1 и 2) |

## KEEP — продуктовые заметки (архив)

| Источник | Куда |
|----------|------|
| `docs/new_spec_ideas.md` | `notes_tz/` |
| черновики `agent_docs/.../tz2026*` | `notes_tz/` |

Актуальные планы — только в `migration/agent_docs/`.

## DROP — не переносим

- весь VLAD/SIFT/`SiftVladEngine`/`FaissVectorIndex` (VLAD)
- `orchestrator.py`, `formatter.py`, `confidence/image.py` (inliers-матрица)
- Pure OCR catalog-wide fallback
- SQLite schema / alembic старого проекта
- старые `_data/vine_base`, set48 crop/full, vina_2026-08-25
- frontend Jinja, старые API endpoints
- paddle/rapid OCR stubs

## ADAPT в новом репо (писать заново, не копировать)

- DINO encode + pgvector top-K → `RankedHit`
- Decision policy: margin / OCR-rerank / not_found (+ флаги enable_*)
- `POST /v1/eval/predict` → `{"slug":"..."}`
- Product UI: одна карточка + аналоги
- Docker Compose: Postgres+pgvector, доступ localhost и сеть compose
- Импорт нового каталога + доп. поля
- Сомелье и retention-фичи
