"""LLM transport, task factory, and adapters (Stage 2A)."""

from __future__ import annotations

__all__ = ["LLMEngine", "create_llm_engine"]


def __getattr__(name: str) -> object:
    if name == "LLMEngine":
        from llm.engine import LLMEngine

        return LLMEngine
    if name == "create_llm_engine":
        from llm.factory import create_llm_engine

        return create_llm_engine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
