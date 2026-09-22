# Config samples (OCR / cropper / compute)

Старый монолитный `search_config.yaml` содержал VLAD/SIFT — **не** копируем целиком.

Здесь только то, что переиспользуем для OCR-rerank и кропа. Пороги DINO и флаги policy — в новом `config/` будущего репо.

## Принцип (как раньше)

1. Числа только в YAML (или env), не в Python.
2. Разделение файлов: `app.yaml` (пути, device, API) vs `search.yaml` / `ocr.yaml` (алгоритм).
3. `compute.device: cpu | cuda` — для провайдеров, которые это умеют (PHOCR; DINO ONNX EP). YOLO cropper в старом коде оставался на CPU; в новом репо можно оставить так же.
4. Всё что относится к настройкам модулей - в конфиги. В .env кладем только например пароли БД, ключи апи, возможно текущий режим (dev, prod) если это требуется для выбора разных конфигурационных файлов
5. Если используются мультирежимные конфиги - должен быть один общий конфиг по умолчанию, потом в него дописываются те поля, которые зависят от текущего режима

## Файлы

- `compute_cropper.yaml` — device, threads, YOLO cropper, пути моделей в `bin/`
- `ocr_rerank.yaml` — PHOCR knobs + fuzzy field weights + rerank_top

Склеить в pydantic-settings в новом проекте (не тащить весь старый `core/config.py`).
