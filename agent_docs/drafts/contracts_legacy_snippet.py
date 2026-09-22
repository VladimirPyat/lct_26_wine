"""TypedDict и Protocol для поиска, кропа и OCR (``IOCREngine`` живёт в ocr.base)."""

from typing import Protocol, TypedDict

from core.ocr.base import IOCREngine

__all__ = [
    "CropResult",
    "IOCREngine",
    "ISearchEngine",
    "LabelCropper",
    "SearchResponse",
    "SearchResult",
]


class SearchResult(TypedDict):
    """Один ранжированный матч вина на стадии каскада."""

    wine_id: int
    external_id: int
    score: float
    inliers: int | None
    good_matches: int | None
    vlad_rank: int | None
    image_path: str


class SearchResponse(TypedDict):
    """Полный выход каскада: VLAD-шортлист, SIFT-ранг, финал и тайминги."""

    vlad_candidates: list[SearchResult]
    sift_ranked: list[SearchResult]
    final: list[SearchResult]
    timings_ms: dict[str, float]


class ISearchEngine(Protocol):
    """Поиск вина по изображению в индексе каталога."""

    def search_image(
        self, image_path: str, *, crop_fallback: bool = False
    ) -> SearchResponse:
        """Вернуть результаты каскада для изображения ``image_path``."""
        ...


class CropResult(TypedDict):
    """Исход YOLO-кропа этикетки; ``cropped_path`` — None, если кроп пропущен."""

    cropped_path: str | None
    used_fallback: bool


class LabelCropper(Protocol):
    """Детектировать и кропнуть этикетку; иначе вернуть исходное изображение."""

    def crop(self, image_path: str) -> CropResult:
        """Кропнуть этикетку из ``image_path`` или пропустить исходник дальше."""
        ...
