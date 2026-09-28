"""Общий продуктовый контракт: DTO, протокол ``ProductService``, заглушка."""

from core.product.schemas import (
    AnalogSource,
    AnalogsResult,
    Candidate,
    CatalogFilters,
    ConfidenceLevel,
    Dictionaries,
    FeedbackIn,
    OcrHints,
    SearchResult,
    SearchStatus,
    Verdict,
    WineCard,
)
from core.product.service import (
    ProductService,
    SearchNotFoundError,
    UploadRejectedError,
)
from core.product.stub import StubProductService

__all__ = [
    "AnalogSource",
    "AnalogsResult",
    "Candidate",
    "CatalogFilters",
    "ConfidenceLevel",
    "Dictionaries",
    "FeedbackIn",
    "OcrHints",
    "ProductService",
    "SearchNotFoundError",
    "SearchResult",
    "SearchStatus",
    "StubProductService",
    "UploadRejectedError",
    "Verdict",
    "WineCard",
]
