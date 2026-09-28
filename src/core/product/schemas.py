"""DTO продуктового API (контракт ``agent_docs/contracts/product_api.md`` §2)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

ConfidenceLevel = Literal["high", "medium", "low"]
SearchStatus = Literal["found", "low", "not_found"]
AnalogSource = Literal["ocr_filters", "winner_filters", "vector"]
Verdict = Literal["match", "mismatch"]


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class WineCard(_FrozenModel):
    """Карточка вина для UI и JSON API.

    ``color`` — цвет из ``categories.name`` («Красное»); ``shade`` — оттенок
    из ``wines.color`` («Тёмно-рубиновый»), только для отображения.
    """

    slug: str
    title: str
    manufacturer: str
    color: str
    shade: str
    region: str
    grape_variety: str
    sweetness: str | None
    description: str
    public_rating: float | None
    product_url: str | None
    image_url: str
    dishes: list[str] = []
    alcohol_pct: float | None
    serving_temperature: str | None


class Candidate(_FrozenModel):
    """Кандидат векторного поиска (top-K) с косинусной близостью."""

    rank: int
    slug: str
    title: str
    manufacturer: str
    image_url: str
    score: float


class OcrHints(_FrozenModel):
    """Подсказки, извлечённые OCR с этикетки (цвет, сорта, производитель)."""

    color: str | None = None
    grapes: list[str] = []
    manufacturer: str | None = None
    ocr_ran: bool = False


class CatalogFilters(_FrozenModel):
    """Фильтры каталога; UI показывает их как удаляемые чипы."""

    color: str | None = None
    grape: str | None = None
    region: str | None = None
    sweetness: str | None = None
    dish: str | None = None
    exclude_manufacturer: str | None = None
    exclude_slugs: list[str] = []


class AnalogsResult(_FrozenModel):
    """Подборка аналогов: источник, фильтры, вина и общее число совпадений."""

    source: AnalogSource
    filters: CatalogFilters
    hints: OcrHints
    wines: list[WineCard]
    total: int


class SearchResult(_FrozenModel):
    """Результат распознавания фото: победитель, уверенность, кандидаты, аналоги."""

    search_id: str
    created_at: datetime
    status: SearchStatus
    confidence_level: ConfidenceLevel
    score_1: float
    margin: float
    winner: WineCard | None
    candidates: list[Candidate]
    analogs: AnalogsResult | None
    rerank_triggered: bool
    latency_ms: float


class Dictionaries(_FrozenModel):
    """Справочники для фильтров каталога."""

    colors: list[str]
    grapes: list[str]
    regions: list[str]
    sweetness: list[str]
    dishes: list[str]


class FeedbackIn(_FrozenModel):
    """Отзыв пользователя о результате поиска («то вино» / «не то»)."""

    search_id: str
    slug: str | None = None
    verdict: Verdict
