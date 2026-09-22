"""Shared typed contracts for cropper, OCR-rerank, and retrieval adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypedDict


class CropResult(TypedDict):
    cropped_path: str | None
    used_fallback: bool


class LabelCropper(Protocol):
    def crop(self, image_path: str) -> CropResult: ...


@dataclass
class WineRecord:
    id: int
    external_id: int
    title: str
    manufacturer: str
    category: str
    region: str
    color: str
    slug: str
    image_path: str
    product_url: str | None
    faiss_row: int | None  # legacy; replace with pgvector / drop in new schema


class SearchResult(TypedDict):
    """Legacy shape still referenced by fuzzy.rerank; slim down in later stages."""

    wine_id: int
    external_id: int
    score: float
    inliers: int | None
    good_matches: int | None
    vlad_rank: int | None
    image_path: str
