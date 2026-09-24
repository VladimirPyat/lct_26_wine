"""Stage 2A — LLMClient retry behaviour (mocked OpenAI transport)."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from openai import APIConnectionError, APIStatusError

from llm.client import LLMClient


def _chat_response(text: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))]
    )


def _status_error(status_code: int, message: str = "http error") -> APIStatusError:
    response = MagicMock()
    response.status_code = status_code
    response.headers = {}
    response.request = MagicMock()
    return APIStatusError(message, response=response, body=None)


def _connection_error(message: str = "connection failed") -> APIConnectionError:
    return APIConnectionError(message=message, request=MagicMock())


def _make_client(*, retries: int = 3) -> LLMClient:
    return LLMClient(
        api_key="test-key",
        base_url="https://example.test/v1",
        model="test-model",
        retries=retries,
        task_name="ocr_label",
        provider_name="qwen",
        temperature=0.0,
    )


def _patch_create(
    monkeypatch: pytest.MonkeyPatch,
    client: LLMClient,
    side_effect: Any,
) -> MagicMock:
    create = MagicMock(side_effect=side_effect)
    monkeypatch.setattr(client._client.chat.completions, "create", create)
    return create


def test_retries_succeed_on_third_attempt(monkeypatch: pytest.MonkeyPatch) -> None:
    """[TEST-ID] 2A-02 transient fails twice, OK on 3rd → 3 attempts."""
    client = _make_client(retries=3)
    create = _patch_create(
        monkeypatch,
        client,
        [
            _connection_error("fail-1"),
            _status_error(503, "fail-2"),
            _chat_response("ok line"),
        ],
    )

    result = client.chat([{"role": "user", "content": "hi"}])

    assert result == "ok line"
    assert create.call_count == 3


def test_retries_exhausted_after_three_fails(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """[TEST-ID] 2A-03 three transient fails → raise; no 4th call; error logged."""
    client = _make_client(retries=3)
    create = _patch_create(
        monkeypatch,
        client,
        [
            _status_error(500, "fail-1"),
            _status_error(429, "fail-2"),
            _connection_error("fail-3"),
        ],
    )

    with caplog.at_level(logging.ERROR, logger="llm.client"):
        with pytest.raises(APIConnectionError, match="fail-3"):
            client.chat([{"role": "user", "content": "hi"}])

    assert create.call_count == 3
    assert any("ocr_label" in r.message and "qwen" in r.message for r in caplog.records)


@pytest.mark.parametrize("status_code", [401, 403])
def test_no_retry_on_auth_errors(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
) -> None:
    """[TEST-ID] 2A-04 HTTP 401/403 → single attempt then fail."""
    client = _make_client(retries=3)
    create = _patch_create(
        monkeypatch,
        client,
        [_status_error(status_code, f"auth-{status_code}")],
    )

    with pytest.raises(APIStatusError) as exc_info:
        client.chat([{"role": "user", "content": "hi"}])

    assert exc_info.value.status_code == status_code
    assert create.call_count == 1
