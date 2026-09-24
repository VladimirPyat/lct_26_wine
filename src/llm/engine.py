"""Thin LLM engine used by task adapters."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any, Literal

from llm.client import LLMClient

OutputKind = Literal["text_lines"]
Modality = Literal["vision", "text"]


class LLMEngine:
    """Invoke a named task: prompt + optional image → parsed output."""

    def __init__(
        self,
        *,
        client: LLMClient,
        prompt: str,
        modality: Modality,
        output_kind: OutputKind,
        task_name: str,
    ) -> None:
        self._client = client
        self._prompt = prompt
        self._modality = modality
        self._output_kind = output_kind
        self.task_name = task_name

    def complete(self, *, image_path: str | None = None) -> list[str]:
        """Run the task and return parsed output (``text_lines`` → ``list[str]``).

        For ``modality=vision``, ``image_path`` is required and must exist.
        """
        messages = self._build_messages(image_path=image_path)
        raw = self._client.chat(messages)
        return self._parse_output(raw)

    def _build_messages(
        self,
        *,
        image_path: str | None,
    ) -> list[dict[str, Any]]:
        if self._modality == "vision":
            if not image_path:
                msg = (
                    f"Task {self.task_name!r} requires image_path "
                    "(modality=vision)"
                )
                raise ValueError(msg)
            source = Path(image_path)
            if not source.is_file():
                msg = f"Image not found for LLM task {self.task_name!r}: {image_path}"
                raise FileNotFoundError(msg)
            data_url = _image_data_url(source)
            content: list[dict[str, Any]] = [
                {"type": "text", "text": self._prompt},
                {"type": "image_url", "image_url": {"url": data_url}},
            ]
            return [{"role": "user", "content": content}]

        # text modality — prompt only
        return [{"role": "user", "content": self._prompt}]

    def _parse_output(self, raw: str) -> list[str]:
        if self._output_kind == "text_lines":
            return _parse_text_lines(raw)
        msg = (
            f"Unsupported output.kind {self._output_kind!r} "
            f"for task {self.task_name!r}"
        )
        raise ValueError(msg)


def _parse_text_lines(raw: str) -> list[str]:
    """Split model text into non-empty stripped lines."""
    lines: list[str] = []
    for part in raw.splitlines():
        stripped = part.strip()
        if stripped:
            lines.append(stripped)
    return lines


def _image_data_url(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    if mime is None:
        mime = "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"
