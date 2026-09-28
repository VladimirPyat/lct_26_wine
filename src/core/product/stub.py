"""Детерминированная заглушка ``ProductService`` для разработки UI (без БД)."""

from __future__ import annotations

import re
import shutil
import tempfile
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from core.product.schemas import (
    AnalogsResult,
    Candidate,
    CatalogFilters,
    ConfidenceLevel,
    Dictionaries,
    FeedbackIn,
    OcrHints,
    SearchResult,
    SearchStatus,
    WineCard,
)
from core.product.service import SearchNotFoundError

_GRAPE_SPLIT = re.compile(r"[,;/+]")

_NOT_FOUND_KEYWORD = "notfound"
_LOW_KEYWORD = "low"

# status -> (confidence_level, score_1, margin, rerank_triggered)
_STATUS_SCORES: dict[SearchStatus, tuple[ConfidenceLevel, float, float, bool]] = {
    "found": ("high", 0.91, 0.12, False),
    "low": ("low", 0.58, 0.02, True),
    "not_found": ("low", 0.41, 0.01, True),
}
_CANDIDATE_SCORE_STEP = 0.03

_STUB_HINTS = OcrHints(
    color="Красное",
    grapes=["Каберне Совиньон"],
    manufacturer=None,
    ocr_ran=True,
)
_DEFAULT_ANALOGS_LIMIT = 5


def _image_url(slug: str) -> str:
    return f"/static/wines/{slug}.webp"


def _fixture_wines() -> list[WineCard]:
    slugs = [
        "abrau-dyurso-abrau-estates-krasnoe-kaberne-sovinon-suhoe-13",
        "fanagoriya-101-ottenok-krasnogo-kaberne-kaberne-sovinon-krasnoe-suhoe-14",
        "olymp-winery-adagum-estate-rose-kaberne-sovinon-rozovoe-suhoe-11",
        "cantiani-aligote-riesling",
        "usadba-rodnoe-gnezdo-4-elements-sovinon-blan-beloe-polusladkoe-12",
    ]
    return [
        WineCard(
            slug=slugs[0],
            title="Abrau Estates красное",
            manufacturer="Абрау-Дюрсо",
            color="Красное",
            shade="Тёмно-гранатовый",
            region="Кубань",
            grape_variety="Каберне Совиньон, Мерло",
            sweetness="сухое",
            description=(
                "В аромате фрукты, табак, чернослив, шоколад и мускатный орех. "
                "Вкус свежий, с мягкими танинами."
            ),
            public_rating=5.0,
            product_url=f"https://vino-svoe.ru/wines/{slugs[0]}",
            image_url=_image_url(slugs[0]),
            dishes=["Мясное ассорти", "Сыры"],
            alcohol_pct=13.0,
            serving_temperature="16-18°C",
        ),
        WineCard(
            slug=slugs[1],
            title="101 оттенок красного. Каберне",
            manufacturer="Фанагория",
            color="Красное",
            shade="Тёмно-рубиновый",
            region="Кубань",
            grape_variety="Каберне Совиньон",
            sweetness="сухое",
            description=(
                "В аромате чёрная смородина, ежевика, слива, лёгкие древесные ноты. "
                "Вкус насыщенный, с округлыми танинами."
            ),
            public_rating=4.3,
            product_url=f"https://vino-svoe.ru/wines/{slugs[1]}",
            image_url=_image_url(slugs[1]),
            dishes=["BBQ", "Мясное ассорти", "Паштеты", "Сыры"],
            alcohol_pct=14.0,
            serving_temperature="16-18°C",
        ),
        WineCard(
            slug=slugs[2],
            title="Adagum Estate Rose",
            manufacturer="Olymp Winery",
            color="Розовое",
            shade="Нежный бледно-лососевый",
            region="Кубань",
            grape_variety="Каберне Совиньон, Мерло",
            sweetness="сухое",
            description=(
                "Свежий, деликатный аромат с тонами клубники, граната "
                "и красной смородины."
            ),
            public_rating=3.9,
            product_url=None,
            image_url=_image_url(slugs[2]),
            dishes=["Блюда из птицы", "Рыба и морепродукты"],
            alcohol_pct=11.0,
            serving_temperature="10-12°C",
        ),
        WineCard(
            slug=slugs[3],
            title="Cantiani Aligote Riesling",
            manufacturer="Шато АЛВИСА",
            color="Белое",
            shade="Светло-золотистый",
            region="Дагестан",
            grape_variety="Алиготе, Рислинг Рейнский",
            sweetness="сухое",
            description=(
                "Аромат яркий и сложный: акация, луговые травы, "
                "зелёное яблоко, цитрусы."
            ),
            public_rating=4.8,
            product_url=f"https://vino-svoe.ru/wines/{slugs[3]}",
            image_url=_image_url(slugs[3]),
            dishes=[
                "Блюда из птицы",
                "Блюда из рыбы",
                "Легкие закуски",
                "Морепродукты",
            ],
            alcohol_pct=12.0,
            serving_temperature="8-10°C",
        ),
        WineCard(
            slug=slugs[4],
            title="4 elements. Совиньон Блан",
            manufacturer="Усадьба Родное Гнездо",
            color="Белое",
            shade="Светло-соломенный",
            region="Крым",
            grape_variety="Совиньон Блан",
            sweetness="полусладкое",
            description=(
                "Насыщенный вкус с тонкими медовыми тонами: груша, дюшес, "
                "зелёное яблоко."
            ),
            public_rating=None,
            product_url=f"https://vino-svoe.ru/wines/{slugs[4]}",
            image_url=_image_url(slugs[4]),
            dishes=["Выпечка и десерты", "Салаты", "Фрукты"],
            alcohol_pct=12.0,
            serving_temperature="10-12°C",
        ),
    ]


def _split_grapes(grape_variety: str) -> list[str]:
    return [part.strip() for part in _GRAPE_SPLIT.split(grape_variety) if part.strip()]


def _eq(left: str | None, right: str) -> bool:
    return left is not None and left.casefold() == right.casefold()


def _matches(wine: WineCard, filters: CatalogFilters) -> bool:
    if filters.color is not None and not _eq(wine.color, filters.color):
        return False
    if filters.region is not None and not _eq(wine.region, filters.region):
        return False
    if filters.sweetness is not None and not _eq(wine.sweetness, filters.sweetness):
        return False
    if filters.grape is not None and not any(
        _eq(grape, filters.grape) for grape in _split_grapes(wine.grape_variety)
    ):
        return False
    if filters.dish is not None and not any(
        _eq(dish, filters.dish) for dish in wine.dishes
    ):
        return False
    if filters.exclude_manufacturer is not None and _eq(
        wine.manufacturer, filters.exclude_manufacturer
    ):
        return False
    return wine.slug not in filters.exclude_slugs


def _rating_key(wine: WineCard) -> tuple[bool, float, str]:
    rating = wine.public_rating
    return (rating is None, -(rating or 0.0), wine.slug)


def _status_for(name: str) -> SearchStatus:
    lowered = name.casefold()
    if _NOT_FOUND_KEYWORD in lowered:
        return "not_found"
    if _LOW_KEYWORD in lowered:
        return "low"
    return "found"


class StubProductService:
    """Заглушка ``ProductService``: 5 фикстурных вин, результаты в памяти.

    Статус поиска выбирается по имени файла: ``notfound`` → ``not_found``,
    ``low`` → ``low``, иначе ``found``/``high``. Фото запросов копируются
    во временный каталог процесса.
    """

    def __init__(self) -> None:
        self._wines = _fixture_wines()
        self._by_slug = {wine.slug: wine for wine in self._wines}
        self._queries_dir = Path(tempfile.mkdtemp(prefix="vine_stub_queries_"))
        self._lock = threading.Lock()
        self._searches: dict[str, SearchResult] = {}
        self._photos: dict[str, Path] = {}
        self._feedback: list[FeedbackIn] = []

    @property
    def feedback(self) -> list[FeedbackIn]:
        """Копия сохранённых отзывов (для тестов и отладки)."""
        with self._lock:
            return list(self._feedback)

    def search(
        self, image_path: Path, *, original_name: str | None = None
    ) -> SearchResult:
        """Скопировать фото и вернуть фикстурный результат по слову в имени файла."""
        started = time.perf_counter()
        search_id = uuid.uuid4().hex
        photo_path = self._queries_dir / f"{search_id}{image_path.suffix.lower()}"
        shutil.copyfile(image_path, photo_path)

        status = _status_for(original_name or image_path.name)
        confidence_level, score_1, margin, rerank_triggered = _STATUS_SCORES[status]
        winner = None if status == "not_found" else self._wines[0]
        candidates = [
            Candidate(
                rank=rank,
                slug=wine.slug,
                title=wine.title,
                manufacturer=wine.manufacturer,
                image_url=wine.image_url,
                score=round(score_1 - (rank - 1) * _CANDIDATE_SCORE_STEP, 4),
            )
            for rank, wine in enumerate(self._wines, start=1)
        ]
        analogs = (
            None
            if status == "found"
            else self._ocr_analogs(winner, limit=_DEFAULT_ANALOGS_LIMIT)
        )
        result = SearchResult(
            search_id=search_id,
            created_at=datetime.now(UTC),
            status=status,
            confidence_level=confidence_level,
            score_1=score_1,
            margin=margin,
            winner=winner,
            candidates=candidates,
            analogs=analogs,
            rerank_triggered=rerank_triggered,
            latency_ms=(time.perf_counter() - started) * 1000.0,
        )
        with self._lock:
            self._searches[search_id] = result
            self._photos[search_id] = photo_path
        return result

    def get_search(self, search_id: str) -> SearchResult | None:
        """Результат поиска из памяти или ``None``."""
        with self._lock:
            return self._searches.get(search_id)

    def query_photo_path(self, search_id: str) -> Path | None:
        """Путь к скопированному фото запроса или ``None``."""
        with self._lock:
            return self._photos.get(search_id)

    def analogs_for(self, search_id: str, *, limit: int = 5) -> AnalogsResult:
        """Аналоги: OCR-фильтры для low/not_found, фильтры победителя для found."""
        result = self.get_search(search_id)
        if result is None:
            msg = f"unknown search_id: {search_id!r}"
            raise SearchNotFoundError(msg)
        if result.status != "found" or result.winner is None:
            return self._ocr_analogs(result.winner, limit=limit)

        winner = result.winner
        grapes = _split_grapes(winner.grape_variety)
        filters = CatalogFilters(
            color=winner.color,
            grape=grapes[0] if grapes else None,
            exclude_manufacturer=winner.manufacturer,
            exclude_slugs=[winner.slug],
        )
        wines, total = self.find_wines(filters, limit=limit)
        if total > 0:
            return AnalogsResult(
                source="winner_filters",
                filters=filters,
                hints=OcrHints(),
                wines=wines,
                total=total,
            )
        vector_wines = [
            self._by_slug[c.slug] for c in result.candidates if c.rank > 1
        ]
        return AnalogsResult(
            source="vector",
            filters=CatalogFilters(),
            hints=OcrHints(),
            wines=vector_wines[:limit],
            total=len(vector_wines),
        )

    def get_wine(self, slug: str) -> WineCard | None:
        """Фикстурная карточка по slug или ``None``."""
        return self._by_slug.get(slug)

    def find_wines(
        self, filters: CatalogFilters, *, limit: int = 5, offset: int = 0
    ) -> tuple[list[WineCard], int]:
        """Фильтрация фикстур в памяти, сортировка по рейтингу (``None`` в конце)."""
        matched = sorted(
            (wine for wine in self._wines if _matches(wine, filters)), key=_rating_key
        )
        return matched[offset : offset + limit], len(matched)

    def dictionaries(self) -> Dictionaries:
        """Справочники, собранные из фикстур."""

        def uniq(values: list[str]) -> list[str]:
            return sorted(set(values), key=str.casefold)

        wines = self._wines
        return Dictionaries(
            colors=uniq([w.color for w in wines]),
            grapes=uniq([g for w in wines for g in _split_grapes(w.grape_variety)]),
            regions=uniq([w.region for w in wines]),
            sweetness=uniq([w.sweetness for w in wines if w.sweetness is not None]),
            dishes=uniq([d for w in wines for d in w.dishes]),
        )

    def record_feedback(self, feedback: FeedbackIn) -> None:
        """Сохранить отзыв в памяти; неизвестный поиск → ``SearchNotFoundError``."""
        with self._lock:
            if feedback.search_id not in self._searches:
                msg = f"unknown search_id: {feedback.search_id!r}"
                raise SearchNotFoundError(msg)
            self._feedback.append(feedback)

    def _ocr_analogs(self, winner: WineCard | None, *, limit: int) -> AnalogsResult:
        filters = CatalogFilters(
            color=_STUB_HINTS.color,
            grape=_STUB_HINTS.grapes[0],
            exclude_slugs=[winner.slug] if winner is not None else [],
        )
        wines, total = self.find_wines(filters, limit=limit)
        return AnalogsResult(
            source="ocr_filters",
            filters=filters,
            hints=_STUB_HINTS,
            wines=wines,
            total=total,
        )
