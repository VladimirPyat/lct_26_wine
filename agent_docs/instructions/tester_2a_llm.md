# @Tester — Stage 2A LLM + OCR adapter

**After:** @Coder finishes [`coder_2a_llm.md`](coder_2a_llm.md) (`READY_FOR_TEST` in progress).  
**Contracts:** [`../contracts/llm_engine.md`](../contracts/llm_engine.md), [`../contracts/ocr_engine.md`](../contracts/ocr_engine.md)

## Goal

Unit-test LLM factory, retries, missing-key fail-fast, and OCR adapter I/O — **without** requiring a live Qwen call in CI. Optional live smoke only if key present and explicitly marked.

## Setup

```bash
uv sync --extra ml --extra db --extra dev
# Do not read or print .env in reports
```

## Cases (minimum)

1. **Missing API key** — unset `QWEN_API_KEY` (or whatever `api_key_env` is) → `create_llm_engine("ocr_label")` raises **`ValueError`**.
2. **Retries success** — mock transport fails twice (transient), succeeds on 3rd → result OK; assert 3 attempts.
3. **Retries exhausted** — mock fails 3 times → error logged + exception; no 4th call.
4. **No retry on 401/403** — single attempt then fail.
5. **OCR adapter shape** — mock LLM / mock HTTP → `recognize(image_path) -> list[str]` (non-empty lines stripped).
6. **Engine swap** — factory or config selects `phocr` mock vs `llm` mock; both satisfy `IOCREngine`.

Do **not** call real DashScope in default pytest path. If adding a live optional test: `pytest.mark.integration` + skip without key.

## Commands

```bash
uv run pytest tests/ -v -k "llm or ocr"
uv run ruff check src/ tests/
```

## Out of scope

- owner_eval / hit@1 (2B)
- Filling `manual_testing.md` (2B tester)

## Report

Write `agent_docs/reports/test_stage_2a_llm.md`. Append status to `agent_docs/progress/stage_2.md`.
