"""Модели представления (view models) страниц, собранные из DTO ``ProductService``."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from math import ceil
from urllib.parse import urlencode

from core.product import (
    AnalogsResult,
    CatalogFilters,
    Dictionaries,
    SearchResult,
    WineCard,
)

CATALOG_PAGE_SIZE = 20

_ANALOG_TITLES: dict[str, str] = {
    "ocr_filters": "Похожие по этикетке",
    "winner_filters": "Аналоги от других виноделен",
    "vector": "Похожие по виду",
}
# Sommelier stub chips: label -> casefolded stem looked up in dictionaries.dishes.
_SOMMELIER_DISHES: tuple[tuple[str, str], ...] = (
    ("Мясо", "мяс"),
    ("Рыба", "рыб"),
    ("Сыры", "сыр"),
)
_SCALAR_FILTERS: tuple[str, ...] = (
    "color",
    "grape",
    "region",
    "sweetness",
    "dish",
    "exclude_manufacturer",
)


@dataclass(frozen=True)
class Chip:
    """Активный фильтр: подпись и ссылка на каталог без этого фильтра."""

    label: str
    remove_url: str


@dataclass(frozen=True)
class DishLink:
    """Чип «Цифрового сомелье»; ``url=None`` — блюда нет в справочнике."""

    label: str
    url: str | None


@dataclass(frozen=True)
class AnalogsView:
    """Блок аналогов на странице результата."""

    title: str
    source: str
    chips: list[Chip]
    wines: list[WineCard]
    total: int
    catalog_url: str
    show_all_url: str | None


@dataclass(frozen=True)
class ResultView:
    """Страница результата поиска для любого статуса (found / low / not_found)."""

    search_id: str
    status: str
    level: str
    winner: WineCard | None
    analogs: AnalogsView | None
    show_analogs_button: bool
    feedback_sent: bool
    feedback_verdict: str | None
    result_url: str
    photo_url: str
    feedback_url: str
    analogs_url: str
    refine_url: str
    sommelier: list[DishLink] = field(default_factory=list)


@dataclass(frozen=True)
class PageLink:
    """Ссылка пагинации."""

    number: int
    url: str
    current: bool


@dataclass(frozen=True)
class CatalogView:
    """Страница каталога: фильтры, выдача и пагинация."""

    filters: CatalogFilters
    dictionaries: Dictionaries
    wines: list[WineCard]
    total: int
    page: int
    pages: int
    chips: list[Chip]
    page_links: list[PageLink]
    prev_url: str | None
    next_url: str | None
    reset_url: str


def catalog_url(filters: CatalogFilters, *, page: int = 1) -> str:
    """URL каталога с непустыми фильтрами (``exclude_slugs`` — повторяющийся ключ)."""
    pairs: list[tuple[str, str]] = []
    for name in _SCALAR_FILTERS:
        value = getattr(filters, name)
        if value:
            pairs.append((name, value))
    pairs.extend(("exclude_slugs", slug) for slug in filters.exclude_slugs)
    if page > 1:
        pairs.append(("page", str(page)))
    return "/catalog" + (f"?{urlencode(pairs)}" if pairs else "")


def filter_chips(filters: CatalogFilters) -> list[Chip]:
    """Чипы активных фильтров со ссылками «убрать фильтр»."""
    labels: dict[str, str] = {
        "dish": "К блюду: {}",
        "exclude_manufacturer": "Кроме винодельни: {}",
    }
    chips: list[Chip] = []
    for name in _SCALAR_FILTERS:
        value = getattr(filters, name)
        if not value:
            continue
        without = filters.model_copy(update={name: None})
        chips.append(
            Chip(
                label=labels.get(name, "{}").format(value),
                remove_url=catalog_url(without),
            )
        )
    if filters.exclude_slugs:
        without = filters.model_copy(update={"exclude_slugs": []})
        chips.append(Chip(label="Без найденного вина", remove_url=catalog_url(without)))
    return chips


def filters_from_query(
    params: Mapping[str, str], exclude_slugs: list[str]
) -> CatalogFilters:
    """Фильтры каталога из query-параметров (пустые значения игнорируются)."""
    values: dict[str, str | None] = {}
    for name in _SCALAR_FILTERS:
        raw = params.get(name, "").strip()
        values[name] = raw or None
    return CatalogFilters(
        color=values["color"],
        grape=values["grape"],
        region=values["region"],
        sweetness=values["sweetness"],
        dish=values["dish"],
        exclude_manufacturer=values["exclude_manufacturer"],
        exclude_slugs=[slug.strip() for slug in exclude_slugs if slug.strip()],
    )


def build_analogs_view(analogs: AnalogsResult) -> AnalogsView:
    """Блок аналогов: заголовок по источнику, чипы, ссылка «Показать все»."""
    all_url = catalog_url(analogs.filters)
    return AnalogsView(
        title=_ANALOG_TITLES.get(analogs.source, "Похожие вина"),
        source=analogs.source,
        chips=filter_chips(analogs.filters),
        wines=list(analogs.wines),
        total=analogs.total,
        catalog_url=all_url,
        show_all_url=all_url if analogs.total > len(analogs.wines) else None,
    )


def build_sommelier(dictionaries: Dictionaries) -> list[DishLink]:
    """Чипы заглушки «Цифровой сомелье» → ``/catalog?dish=…`` из справочника блюд."""
    links: list[DishLink] = []
    for label, stem in _SOMMELIER_DISHES:
        dish = next((d for d in dictionaries.dishes if stem in d.casefold()), None)
        url = catalog_url(CatalogFilters(dish=dish)) if dish is not None else None
        links.append(DishLink(label=label, url=url))
    return links


def build_result_view(
    result: SearchResult,
    *,
    extra_analogs: AnalogsResult | None,
    feedback_verdict: str | None,
    feedback_sent: bool,
    dictionaries: Dictionaries,
) -> ResultView:
    """Собрать страницу результата; ``extra_analogs`` — аналоги по кнопке (found)."""
    analogs_dto = result.analogs if result.analogs is not None else extra_analogs
    analogs = build_analogs_view(analogs_dto) if analogs_dto is not None else None
    base = f"/result/{result.search_id}"
    refine = analogs.catalog_url if analogs is not None else "/catalog"
    return ResultView(
        search_id=result.search_id,
        status=result.status,
        level=result.confidence_level,
        winner=result.winner,
        analogs=analogs,
        show_analogs_button=result.status == "found" and analogs is None,
        feedback_sent=feedback_sent,
        feedback_verdict=feedback_verdict,
        result_url=base,
        photo_url=f"{base}/photo",
        feedback_url=f"{base}/feedback",
        analogs_url=f"{base}?analogs=1#analogs",
        refine_url=refine,
        sommelier=build_sommelier(dictionaries),
    )


def build_catalog_view(
    filters: CatalogFilters,
    *,
    dictionaries: Dictionaries,
    wines: list[WineCard],
    total: int,
    page: int,
) -> CatalogView:
    """Страница каталога с пагинацией по ``CATALOG_PAGE_SIZE``."""
    pages = max(1, ceil(total / CATALOG_PAGE_SIZE))
    page_links = [
        PageLink(number=n, url=catalog_url(filters, page=n), current=n == page)
        for n in range(1, pages + 1)
    ]
    return CatalogView(
        filters=filters,
        dictionaries=dictionaries,
        wines=wines,
        total=total,
        page=page,
        pages=pages,
        chips=filter_chips(filters),
        page_links=page_links,
        prev_url=catalog_url(filters, page=page - 1) if page > 1 else None,
        next_url=catalog_url(filters, page=page + 1) if page < pages else None,
        reset_url="/catalog",
    )
