"""Adapters that expose LLM tasks behind existing core interfaces."""

from __future__ import annotations

__all__ = ["LLMOCREngine"]


def __getattr__(name: str) -> object:
    if name == "LLMOCREngine":
        from llm.adapters.ocr import LLMOCREngine

        return LLMOCREngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
