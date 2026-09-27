"""Shared typed contracts for cropper, OCR-rerank, and retrieval adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import NotRequired, Protocol, TypedDict


class CropResult(TypedDict):
    cropped_path: str | None
    used_fallback: bool


class LabelCropper(Protocol):
    def crop(self, image_path: str) -> CropResult: ...


class RankedHit(TypedDict):
    """pgvector top-K hit (higher ``score`` = better cosine similarity).

    ``image_path`` holds the public catalog path from ``wines.image_url``
    (e.g. ``/static/wines/{slug}.webp``).
    """

    wine_id: int
    slug: str
    score: float
    title: str
    manufacturer: str
    category: str
    image_path: str
    grape_variety: NotRequired[str]


class IRetriever(Protocol):
    def retrieve(self, image_path: str, *, top_k: int) -> list[RankedHit]: ...


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
