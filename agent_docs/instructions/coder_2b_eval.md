# @Coder — Stage 2B Eval API + orchestrator

**Depends on:** Stage 1 catalog + embeddings; YOLO/DINO/PHOCR/Fuzzy already in tree.  
**Contracts:** [`../contracts/eval_predict.md`](../contracts/eval_predict.md), [`../contracts/retrieval.md`](../contracts/retrieval.md), [`../contracts/ocr_engine.md`](../contracts/ocr_engine.md)  
**Tester:** [`tester_2b_eval.md`](tester_2b_eval.md)  
**LLM OCR:** if `ocr.engine=llm`, requires [`coder_2a_llm.md`](coder_2a_llm.md). Default local path may use `phocr`; Qwen/`llm` is the configured alternate (primary remote/CPU path).

## Goal

Wire YOLO → DINO → pgvector top-K → decision policy → `POST /v1/eval/predict` always returning best `slug`. Structured decision logs + report collector script.

## Dependencies

```bash
uv sync --extra ml --extra db --extra dev
```

No new packages beyond what 2A already added unless a gap blocks (then `BLOCKED.md` — do not improvise).

## Steps

1. **Retriever** — implement `IRetriever.retrieve(image_path, top_k)`: crop → encode → `search_by_embedding`.

2. **Policy** in `src/core/policy/` per [eval_predict.md](../contracts/eval_predict.md):
   - Knobs in YAML: `top_k: 5`, `margin_min: 0.1`, `abs_min: 0.2`, `enable_rerank: true`
   - Skip OCR when `not enable_rerank` or `margin >= margin_min` or single hit
   - Else `IOCREngine.recognize` + `FuzzyReranker` on pool
   - `score_1 < abs_min` → log garbage flag; **still** return top-1 slug
   - Eval never returns null slug when hits exist

3. **API** — `POST /v1/eval/predict` multipart field `image` → `{"slug": "..."}` (200/201). Wire into `src/api/main.py` (or routers). Temp file cleanup.

4. **Structured logging** — per-request JSON (or dedicated logger): top-k scores, margin, garbage, rerank flags, engine, latency breakdown. Not in HTTP body.

5. **Report script** — `scripts/collect_eval_report.py`: ingest decision log (+ optional `mapping.json`) → hit@1, rerank rate, garbage rate, latency p50/p95. Document CLI in configuration_guide / quickstart.

6. **Config** — merge policy flags into existing YAML (`config/ocr_rerank.yaml` or new `config/policy.yaml`); wire `ocr.engine`.

7. **Docs (required)**
   - `manuals/architecture.md` — eval pipeline + policy + logs
   - `manuals/configuration_guide.md` — policy knobs, ocr.engine, log path
   - `manuals/quickstart.md` — uvicorn + owner_eval set1 command from `tooling.mdc`
   - Do **not** invent `manual_testing.md` content (stub exists; @Tester fills)

## Out of scope

- Product card / not_found UI (Stage 3)
- Threshold calibration beyond YAML defaults
- Changing organizer `participant_test.sh`

## Acceptance

- [ ] Harness set1 can call endpoint and write `predictions.jsonl`
- [ ] Response always has non-empty slug when DB has hits
- [ ] Logs contain top-k; report script runs on a sample log
- [ ] `enable_rerank: false` skips OCR
- [ ] Manuals updated

## Handoff

Append `READY_FOR_TEST` (2B) to `agent_docs/progress/stage_2.md`. Lint gate on `src/`.
