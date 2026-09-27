# Config samples (OCR / cropper / compute)

Старый монолитный `search_config.yaml` содержал VLAD/SIFT — **не** копируем целиком.

Здесь только то, что переиспользуем для OCR-rerank, кропа и энкодера изображений (SigLIP2). Флаги policy — в `ocr_rerank.yaml`.

## Принцип (как раньше)

1. Числа только в YAML (или env), не в Python.
2. Разделение файлов: `app.yaml` (пути, device, API) vs `search.yaml` / `ocr.yaml` (алгоритм).
3. `compute.device: cpu | cuda` — для провайдеров, которые это умеют (PHOCR; ONNX EP энкодера изображений SigLIP2). YOLO cropper в старом коде оставался на CPU; в новом репо можно оставить так же.
4. Всё что относится к настройкам модулей - в конфиги. В .env кладем только например пароли БД, ключи апи, возможно текущий режим (dev, prod) если это требуется для выбора разных конфигурационных файлов
5. Если используются мультирежимные конфиги - должен быть один общий конфиг по умолчанию, потом в него дописываются те поля, которые зависят от текущего режима

## Файлы

- `compute_cropper.yaml` — device, threads, YOLO cropper, пути моделей в `bin/`
- `database.yaml` — `embedding_dim` (1152), путь к `siglip2_wine_p1_epoch_3.onnx`, блок `dino` (историческое имя; input_size / `resize_mode: letterbox` / `pad_fill_rgb` / mean-std 0.5 / L2). Блок DINOv2 оставлен закомментированным для отката
- `ocr_rerank.yaml` — PHOCR knobs + fuzzy field weights + rerank_top

Склеить в pydantic-settings в новом проекте (не тащить весь старый `core/config.py`).
