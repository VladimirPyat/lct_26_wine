"""Протокол ``ProductService`` и его исключения (контракт ``product_api.md`` §3)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from core.product.schemas import (
    AnalogsResult,
    CatalogFilters,
    Dictionaries,
    FeedbackIn,
    SearchResult,
    WineCard,
)


class SearchNotFoundError(LookupError):
    """Поиск с указанным ``search_id`` не найден."""


class UploadRejectedError(ValueError):
    """Загруженный файл не удалось декодировать как изображение."""


class ProductService(Protocol):
    """Общий продуктовый сервис для JSON API и Jinja UI.

    Все методы синхронные (CPU/GPU + БД); роуты FastAPI вызывают их
    через ``run_in_threadpool``.
    """

    def search(
        self, image_path: Path, *, original_name: str | None = None
    ) -> SearchResult:
        """Распознать вино на фото.

        Сервис копирует ``image_path`` в своё хранилище; временный файл
        удаляет вызывающий. Может бросить ``UploadRejectedError``.
        """
        ...

    def get_search(self, search_id: str) -> SearchResult | None:
        """Вернуть сохранённый результат поиска или ``None``."""
        ...

    def query_photo_path(self, search_id: str) -> Path | None:
        """Путь к сохранённому фото запроса или ``None`` для неизвестного id."""
        ...

    def analogs_for(self, search_id: str, *, limit: int = 5) -> AnalogsResult:
        """Подобрать аналоги для поиска; неизвестный id → ``SearchNotFoundError``."""
        ...

    def get_wine(self, slug: str) -> WineCard | None:
        """Карточка вина по slug или ``None``."""
        ...

    def find_wines(
        self, filters: CatalogFilters, *, limit: int = 5, offset: int = 0
    ) -> tuple[list[WineCard], int]:
        """Вина по фильтрам (рейтинг по убыванию) и общее число совпадений."""
        ...

    def dictionaries(self) -> Dictionaries:
        """Справочники для фильтров каталога."""
        ...

    def record_feedback(self, feedback: FeedbackIn) -> None:
        """Сохранить отзыв; неизвестный ``search_id`` → ``SearchNotFoundError``."""
        ...
