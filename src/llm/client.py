"""OpenAI-compatible HTTP client with retries for transient failures."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)

logger = logging.getLogger(__name__)

_DEFAULT_RETRIES = 3
_RETRYABLE_STATUS = frozenset({408, 429}) | frozenset(range(500, 600))


class LLMClient:
    """Thin OpenAI-compatible chat client; retries connect/timeout/408/429/5xx."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        retries: int = _DEFAULT_RETRIES,
        task_name: str,
        provider_name: str,
        temperature: float = 0.0,
    ) -> None:
        if retries < 1:
            msg = f"retries must be >= 1, got {retries}"
            raise ValueError(msg)
        self._model = model
        self._retries = retries
        self._task_name = task_name
        self._provider_name = provider_name
        self._temperature = temperature
        # Disable SDK retries; this class owns the retry loop for testability.
        self._client = OpenAI(api_key=api_key, base_url=base_url, max_retries=0)

    def chat(
        self,
        messages: Sequence[dict[str, Any]],
    ) -> str:
        """Call chat completions; return assistant text content.

        Retries up to ``retries`` times on transient transport/HTTP errors.
        Non-retryable 4xx (e.g. 401/403/422) fail immediately.
        After exhaustion: log error (task + provider) and re-raise.
        """
        last_error: BaseException | None = None
        for attempt in range(1, self._retries + 1):
            try:
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=list(messages),
                    temperature=self._temperature,
                )
                choice = response.choices[0]
                content = choice.message.content
                if not isinstance(content, str):
                    msg = (
                        f"LLM returned empty content "
                        f"(task={self._task_name}, provider={self._provider_name})"
                    )
                    raise RuntimeError(msg)
                return content
            except Exception as err:
                last_error = err
                if not _is_retryable(err) or attempt >= self._retries:
                    if attempt >= self._retries and _is_retryable(err):
                        logger.error(
                            "LLM call failed after %s attempts "
                            "(task=%s, provider=%s): %s",
                            self._retries,
                            self._task_name,
                            self._provider_name,
                            _error_summary(err),
                        )
                    elif not _is_retryable(err):
                        logger.error(
                            "LLM call failed non-retryable "
                            "(task=%s, provider=%s): %s",
                            self._task_name,
                            self._provider_name,
                            _error_summary(err),
                        )
                    raise
                logger.warning(
                    "LLM transient failure attempt %s/%s "
                    "(task=%s, provider=%s): %s",
                    attempt,
                    self._retries,
                    self._task_name,
                    self._provider_name,
                    _error_summary(err),
                )
        assert last_error is not None  # pragma: no cover
        raise last_error


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, (APIConnectionError, APITimeoutError, RateLimitError)):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code in _RETRYABLE_STATUS
    return False


def _error_summary(exc: BaseException) -> str:
    if isinstance(exc, APIStatusError):
        return f"HTTP {exc.status_code}: {exc}"
    return f"{type(exc).__name__}: {exc}"
