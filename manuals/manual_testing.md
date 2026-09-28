# Ручное тестирование

Чеклист HITL для Stage 2B (eval API + owner_eval). Автотесты: `tests/test_policy_decision.py`, `tests/test_eval_predict_api.py`, `tests/test_owner_eval_scoring.py`.

## Назначение

Проверить вручную: подъём API, прогон owner_eval set1/set2, decision-логи, `collect_eval_report.py`, переключение `ocr.engine` / `enable_rerank`.

## Предусловия

- Postgres: `docker compose up -d` (healthy)
- Зависимости: `uv sync --extra ml --extra db --extra dev`
- Миграции: `uv run alembic upgrade head`
- Каталог загружен (все вина с embedding)
- Веса PHOCR скачаны (первый `recognize` тянет ONNX с modelscope; при таймауте — докачать `ru_rec_decoder_v1.onnx` в `.venv/.../phocr/models/`)
- Команды — из `tooling.mdc` / `manuals/quickstart.md`
- **Не печатать** содержимое `.env` / ключи

## Шаги

### 1. Запуск API

```bash
# убедиться: config/ocr_rerank.yaml → ocr.engine: phocr, policy.enable_rerank: true
: > data/tmp/eval_decisions.jsonl
uv run uvicorn api.main:app --app-dir src --host 0.0.0.0 --port 8080
```

- [ ] `curl -s http://127.0.0.1:8080/health` → `{"status":"ok"}`
- [ ] Smoke:

```bash
curl -s -F "image=@./data/owner_eval/1/queries/04f3ce15.jpg" \
  http://127.0.0.1:8080/v1/eval/predict
```

- Ожидание: HTTP 200, JSON `{"slug":"<непустая-строка>"}`; в `data/tmp/eval_decisions.jsonl` появилась строка с `top_k`, `margin`, `garbage`, `rerank_triggered`, `ocr_engine`, `latency_ms`.

### 2. Owner eval set 1

```bash
./data/owner_eval/1/participant_test.sh \
  --images-dir ./data/owner_eval/1/queries \
  --manifest ./data/owner_eval/1/queries.tsv \
  --endpoint 'http://127.0.0.1:8080/v1/eval/predict' \
  --output ./data/owner_eval/1/predictions.jsonl
```

- [ ] Скрипт завершился с exit 0; в `predictions.jsonl` по одной строке на query (~27); у всех есть непустой `predicted_slug`
- Ожидание: hit@1 vs `mapping.json` → `cases[].expected_slug` (или vs `predictions.golden.jsonl`). Зафиксировать долю hit@1 в отчёте прогона.

### 3. Логи и отчёт

```bash
# mapping.json организатора — формат cases[]; для скрипта нужен плоский {query_id: slug}
python3 -c "
import json
from pathlib import Path
m=json.loads(Path('data/owner_eval/1/mapping.json').read_text())
flat={c['query_id']:c['expected_slug'] for c in m['cases']}
Path('data/tmp/mapping_flat_set1.json').write_text(json.dumps(flat,ensure_ascii=False,indent=2)+'\n')
"

uv run python scripts/collect_eval_report.py \
  --log data/tmp/eval_decisions.jsonl \
  --predictions data/owner_eval/1/predictions.jsonl \
  --mapping data/tmp/mapping_flat_set1.json \
  --json
```

- [ ] Отчёт: `n_requests`, `rerank_rate`, `garbage_rate`, `latency_ms.p50/p95`, `hit_at_1`
- Ожидание: soft latency ~3s (часто выше на CPU + phocr); логи содержат top-k score/slug
- **Известный дефект:** `--mapping data/owner_eval/1/mapping.json` (сырой) → hit@1 = n/a (скрипт не читает `cases`)

### 4. Owner eval set 2

Перед прогоном сохранить лог set1 (`cp data/tmp/eval_decisions.jsonl data/tmp/eval_decisions_set1.jsonl`) или очистить файл осознанно.

```bash
: > data/tmp/eval_decisions.jsonl
./data/owner_eval/2/participant_test.sh \
  --images-dir ./data/owner_eval/2/queries \
  --manifest ./data/owner_eval/2/queries.tsv \
  --endpoint 'http://127.0.0.1:8080/v1/eval/predict' \
  --output ./data/owner_eval/2/predictions.jsonl
```

- [ ] Exit 0; все `predicted_slug` непустые; hit@1 vs set2 mapping/golden
- Ожидание: аналогичный отчёт через `collect_eval_report.py` + `mapping_flat_set2.json`

### 5. Переключение OCR / rerank

Править только `config/ocr_rerank.yaml`, затем **перезапустить** uvicorn.

- [ ] `policy.enable_rerank: false` → в логах `rerank_triggered: false`, OCR не вызывается; slug всё равно возвращается; latency ниже
- [ ] `ocr.engine: llm` (нужен `QWEN_API_KEY` в `.env`, **не печатать**) → в логах `ocr_engine: llm`; slug непустой
- [ ] Вернуть `ocr.engine: phocr`, `enable_rerank: true` для основного приёмочного прогона
- Ожидание: HTTP-тело по-прежнему только `{"slug":"..."}`; детали — только в decision log

### 6. Anti-cheat (опционально вручную)

```bash
uv run pytest tests/test_owner_eval_scoring.py::test_owner_eval_canary_swapped_golden_fails -v
```

- Ожидание: PASS — значит swapped golden даёт hit@1 ≈ 0 (компаратор не «подогнан» под файл)

## Вне scope

Калибровка порогов YAML как «багфикс», UI Stage 4, правка `participant_test.sh`.
