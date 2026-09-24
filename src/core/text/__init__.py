"""Text matching (Levenshtein fuzzy-rerank). Lazy exports avoid heavy imports."""

from __future__ import annotations

__all__ = ["FuzzyReranker", "postprocess_ocr_lines"]


def __getattr__(name: str):
    if name == "FuzzyReranker":
        from core.text.fuzzy import FuzzyReranker

        return FuzzyReranker
    if name == "postprocess_ocr_lines":
        from core.text.ocr_postprocess import postprocess_ocr_lines

        return postprocess_ocr_lines
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
