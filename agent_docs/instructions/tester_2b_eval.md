# @Tester — Stage 2B Eval API + owner_eval

**After:** @Coder finishes [`coder_2b_eval.md`](coder_2b_eval.md) (`READY_FOR_TEST` in progress).  
**Contracts:** [`../contracts/eval_predict.md`](../contracts/eval_predict.md)  
**HITL doc:** fill [`../../manuals/manual_testing.md`](../../manuals/manual_testing.md) (stub created by Planner).

## Goal

Prove policy unit behavior, anti-cheat golden, and organizer harness on set **1**, then set **2**. Fill manual testing steps for humans.

## Setup

```bash
docker compose up -d
uv sync --extra ml --extra db --extra dev
uv run alembic upgrade head
# Catalog must be loaded (Stage 1.2). API:
uv run uvicorn api.main:app --app-dir src --host 0.0.0.0 --port 8080
```

## Cases (minimum)

### Unit / API

1. **Policy margin** — synthetic hits with large margin → no OCR call; small margin + `enable_rerank` → OCR called (mock).
2. **`enable_rerank: false`** — never calls OCR even if margin tiny.
3. **`abs_min` garbage** — low `score_1` → garbage flag in log/decision meta; returned slug still top-1.
4. **HTTP smoke** — multipart `image` → `{"slug": "..."}` status 200/201.

### E2E — `data/owner_eval` (required)

Run against a **live** API (uvicorn as in Setup) and the organizer harness. This is the Stage 2 acceptance path, not optional HITL-only.

5. **Set 1 e2e**

```bash
./data/owner_eval/1/participant_test.sh \
  --images-dir ./data/owner_eval/1/queries \
  --manifest ./data/owner_eval/1/queries.tsv \
  --endpoint 'http://127.0.0.1:8080/v1/eval/predict' \
  --output ./data/owner_eval/1/predictions.jsonl
```

- Assert script finishes; every line has a `predicted_slug` (or document organizer nulls if API failed).
- Compute hit@1 vs `data/owner_eval/1/mapping.json` (and/or `predictions.golden.jsonl`).
- Run `collect_eval_report.py` on decision logs; record hit@1, rerank rate, latency p50/p95 (~3s soft).
- Prefer wrapping harness + hit@1 assert in pytest (`tests/…`) marked `integration` / `e2e` if the suite can start/use a running server; otherwise run the shell + a small pytest that only scores `predictions.jsonl` vs mapping — **both** must appear in the test report.

6. **Set 2 e2e** — same after set1 is green (paths under `data/owner_eval/2/`).

Prefer `ocr.engine=phocr` for primary e2e if GPU/local weights available; optional second pass with `llm` (Qwen) if key present (never print key).

### Canary anti-cheat (required)

7. **Swapped-golden canary** — proves the suite is not fitted to a fixed golden file:

   1. After a **successful** honest check (predictions vs real `predictions.golden.jsonl` / `mapping.json`),  
   2. Copy golden to a **temp** file (do **not** overwrite or commit the real golden).  
   3. **Permute** `predicted_slug` values (e.g. rotate by 1, or swap pairs) so almost no `query_id` keeps the correct slug.  
   4. Re-run the **same** hit@1 comparison against that swapped copy.  

   **Expected: test FAILS** (hit@1 near 0 / below a low ceiling). If this “fails” as a passing green test, the comparator is broken or cheating.

   Automate as a dedicated pytest (e.g. `test_owner_eval_canary_swapped_golden`); keep the real golden untouched.
## Manual testing doc

Fill `manuals/manual_testing.md` with concrete human steps: start API, run set1/set2, where logs live, how to run report script, how to flip `enable_rerank` / `ocr.engine`. Expected checks only — no architecture essays. Sync status line in `manuals/index.md` if needed.

## Commands

```bash
uv run pytest tests/ -v -k "eval or policy or predict"
uv run ruff check src/ tests/
```

## Out of scope

- Product UI
- Tuning YAML thresholds as “code fix” (report suggested values only)

## Report

Write `agent_docs/reports/test_stage_2b_eval.md`: unit results; **e2e set1/set2** hit@1 + latency; **canary** = swapped golden comparison failed as expected; notes. Append to `agent_docs/progress/stage_2.md`.
