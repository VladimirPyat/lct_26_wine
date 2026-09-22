"""OCR engines: MockOCREngine, PHOCREngine (import submodule explicitly to avoid heavy deps)."""

from __future__ import annotations

__all__ = ["IOCREngine", "MockOCREngine", "PHOCREngine"]


def __getattr__(name: str):
    if name == "IOCREngine":
        from core.ocr.base import IOCREngine

        return IOCREngine
    if name == "MockOCREngine":
        from core.ocr.mock import MockOCREngine

        return MockOCREngine
    if name == "PHOCREngine":
        from core.ocr.phocr import PHOCREngine

        return PHOCREngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
