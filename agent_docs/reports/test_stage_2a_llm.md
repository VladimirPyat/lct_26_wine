# Test report — Stage 2A LLM + OCR adapter

**Date:** 2026-09-24  
**Instructions:** `agent_docs/instructions/tester_2a_llm.md`  
**Contracts:** `llm_engine.md`, `ocr_engine.md`  
**Verdict:** **PASS**

## Commands

| Command | Exit code | Result |
|---------|-----------|--------|
| `uv sync --extra ml --extra db --extra dev` | 0 | deps OK (audited) |
| `uv run pytest tests/ -v -k "llm or ocr"` | 0 | 8 passed, 1 skipped, 13 deselected |
| `uv run ruff check src/ tests/` | 0 | All checks passed |

Live DashScope **not** called in default path; transport mocked. Optional `@pytest.mark.integration` smoke skipped (no `QWEN_API_KEY` in process env; secret values not read/printed).

## Cases vs `tester_2a_llm.md`

| # | Case | Test | Result |
|---|------|------|--------|
| 1 | Missing / empty API key → `ValueError` | `test_missing_api_key_raises_value_error`, `test_empty_api_key_raises_value_error` | PASS |
| 2 | Retries success (fail 2×, OK on 3rd) | `test_retries_succeed_on_third_attempt` | PASS |
| 3 | Retries exhausted (3 fails, no 4th; error logged) | `test_retries_exhausted_after_three_fails` | PASS |
| 4 | No retry on 401/403 | `test_no_retry_on_auth_errors[401/403]` | PASS |
| 5 | OCR adapter → `list[str]` stripped | `test_llm_ocr_adapter_returns_stripped_lines` | PASS |
| 6 | Engine swap phocr mock vs llm mock vs mock | `test_ocr_factory_swap_phocr_mock_vs_llm_mock` | PASS |

Optional: `test_optional_live_create_skipped_without_key` — **SKIPPED** (expected without key).

## Artifacts

- `tests/test_llm_client.py`
- `tests/test_llm_factory.py`
- `tests/test_ocr_adapter.py`
- `tests/conftest.py` — marker `integration`

Minor: wrapped long docstring in `tests/test_catalog_load.py` for ruff E501 (pre-existing).

## Defects

None against Stage 2A contracts / acceptance.

## Next

Stage 2A sign-off OK. Do **not** start 2B from this report; @Tester 2B / @Coder 2B separately when ready.
