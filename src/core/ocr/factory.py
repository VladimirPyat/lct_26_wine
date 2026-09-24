"""Factory: select OCR backend from config (``phocr`` | ``llm`` | ``mock``)."""

from __future__ import annotations

from core.ocr.base import IOCREngine
from core.ocr.mock import MockOCREngine


def create_ocr_engine(
    engine: str,
    *,
    llm_task: str = "ocr_label",
    use_cuda: bool | None = None,
    lang: str | None = None,
    limit_side_len: int | None = None,
    ort_threads: int | None = None,
) -> IOCREngine:
    """Собрать ``IOCREngine`` по имени бэкенда.

    ``phocr`` requires ``use_cuda``, ``lang``, ``limit_side_len``, ``ort_threads``.
    ``llm`` uses ``llm_task`` (default ``ocr_label``); no provider URLs here.
    ``mock`` returns empty lines (tests).
    """
    name = engine.strip().lower()
    if name == "mock":
        return MockOCREngine()
    if name == "llm":
        from llm.adapters.ocr import LLMOCREngine

        return LLMOCREngine(task_name=llm_task)
    if name == "phocr":
        if (
            use_cuda is None
            or lang is None
            or limit_side_len is None
            or ort_threads is None
        ):
            msg = (
                "create_ocr_engine(phocr) requires use_cuda, lang, "
                "limit_side_len, and ort_threads"
            )
            raise ValueError(msg)
        from core.ocr.phocr import PHOCREngine

        return PHOCREngine(
            use_cuda=use_cuda,
            lang=lang,
            limit_side_len=limit_side_len,
            ort_threads=ort_threads,
        )
    msg = f"Unknown ocr.engine {engine!r}; expected phocr | llm | mock"
    raise ValueError(msg)
