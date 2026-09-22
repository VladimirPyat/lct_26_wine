# Models in bin/ (ONNX-first)

## Уже в migration/bin

| Файл | Назначение |
|------|------------|
| `yolo_detect_labels_2.onnx` | актуальный кроп этикетки |
| `yolo_detect_labels.onnx` | запасной |

## Добавить вручную (не в git snapshot обязательно)

| Артефакт | Назначение |
|----------|------------|
| `dino_wine.onnx` (имя TBD) | дообученный DINO, инференс без torch |
| веса / пакет PHOCR | чтобы offline-сетап не качал с сети на сдаче |

## Runtime

- `onnxruntime` (CPU) или `onnxruntime-gpu` на машине заказчика.  
- Переключение: `compute.device: cpu | cuda` → выбор ExecutionProvider.  
- `torch` / `transformers` — только для **экспорта/дообучения** в отдельном lab-окружении, не в сервисе сдачи.

## Preprocess

Один и тот же пайплайн для индексации каталога и query (crop YOLO → resize/нормализация как при экспорте ONNX). Иначе top-K «плывёт».
