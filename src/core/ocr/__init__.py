"""OCR engines: MockOCREngine, PHOCREngine, create_ocr_engine (lazy imports)."""

from __future__ import annotations

__all__ = ["IOCREngine", "MockOCREngine", "PHOCREngine", "create_ocr_engine"]


def __getattr__(name: str) -> object:
    if name == "IOCREngine":
        from core.ocr.base import IOCREngine

        return IOCREngine
    if name == "MockOCREngine":
        from core.ocr.mock import MockOCREngine

        return MockOCREngine
    if name == "PHOCREngine":
        from core.ocr.phocr import PHOCREngine

        return PHOCREngine
    if name == "create_ocr_engine":
        from core.ocr.factory import create_ocr_engine

        return create_ocr_engine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
