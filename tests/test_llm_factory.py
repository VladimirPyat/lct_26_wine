"""Stage 2A — create_llm_engine factory (missing key fail-fast)."""

from __future__ import annotations

import pytest

from llm.factory import create_llm_engine


def test_missing_api_key_raises_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """[TEST-ID] 2A-01 unset QWEN_API_KEY → ValueError from create_llm_engine."""
    monkeypatch.delenv("QWEN_API_KEY", raising=False)

    with pytest.raises(ValueError, match="QWEN_API_KEY"):
        create_llm_engine("ocr_label")


def test_empty_api_key_raises_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """[TEST-ID] 2A-01b empty QWEN_API_KEY → ValueError (fail fast)."""
    monkeypatch.setenv("QWEN_API_KEY", "   ")

    with pytest.raises(ValueError, match="QWEN_API_KEY"):
        create_llm_engine("ocr_label")


@pytest.mark.integration
def test_optional_live_create_skipped_without_key() -> None:
    """Optional live smoke: skip when QWEN_API_KEY absent (no DashScope in CI)."""
    import os

    # Do not read or print secret values — only presence.
    if not os.environ.get("QWEN_API_KEY", "").strip():
        pytest.skip("QWEN_API_KEY not set; skip live LLM smoke")

    engine = create_llm_engine("ocr_label")
    assert engine.task_name == "ocr_label"
