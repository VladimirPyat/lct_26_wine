"""PROD-API B — CatalogProductService на Compose Postgres (read-only, без моделей)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from pathlib import Path

import pytest

from core.product.catalog_service import CatalogProductService
from core.product.schemas import Candidate, CatalogFilters, OcrHints, WineCard
from core.product.service import SearchNotFoundError
from core.product.vocabulary import value_key
from db.repository import WineRepository
from db.session import session_scope
from product_helpers import build_db_service, make_result, store_result

pytestmark = pytest.mark.db

ALL = 100_000  # "no limit" for full-list assertions


@pytest.fixture(scope="module")
def service(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[CatalogProductService]:
    svc = build_db_service(tmp_path_factory.mktemp("product_db"))
    yield svc
    svc._runtime.engine.dispose()  # type: ignore[attr-defined]


@pytest.fixture(scope="module")
def queries_dir(service: CatalogProductService) -> Path:
    return service._queries_dir


def _assert_rating_desc_nulls_last(wines: list[WineCard]) -> None:
    ratings = [w.public_rating for w in wines]
    rated = [r for r in ratings if r is not None]
    first_null = next((i for i, r in enumerate(ratings) if r is None), len(ratings))
    assert all(r is None for r in ratings[first_null:]), "NULL rating before rated wine"
    assert rated == sorted(rated, reverse=True), "ratings not DESC"


def _count(service: CatalogProductService, **kwargs: object) -> int:
    with session_scope(service._runtime.session_factory) as session:
        return WineRepository(session).count_filters(**kwargs)  # type: ignore[arg-type]


def _winner_with_rivals(service: CatalogProductService) -> WineCard:
    """Красное вино, у производителя которого ≥2 красных вин."""
    wines, _ = service.find_wines(CatalogFilters(color="Красное"), limit=ALL)
    by_mfr = Counter(w.manufacturer for w in wines)
    for wine in wines:
        if by_mfr[wine.manufacturer] >= 2 and wine.grape_variety.strip():
            return wine
    pytest.skip("no manufacturer with ≥2 red wines in catalog")


# --- find_wines ----------------------------------------------------------


def test_find_wines_color_sorted_and_limited(service: CatalogProductService) -> None:
    """[TEST-ID] PA-B1 color → rating DESC NULLS LAST; limit=5 при total > 5."""
    page, total = service.find_wines(CatalogFilters(color="Красное"), limit=5)
    assert total > 5
    assert len(page) == 5
    assert all(w.color == "Красное" for w in page)
    _assert_rating_desc_nulls_last(page)

    full, full_total = service.find_wines(CatalogFilters(color="Красное"), limit=ALL)
    assert full_total == total == len(full)
    assert all(w.color == "Красное" for w in full)
    _assert_rating_desc_nulls_last(full)
    assert [w.slug for w in full[:5]] == [w.slug for w in page]


def test_find_wines_nulls_last_whole_catalog(service: CatalogProductService) -> None:
    """[TEST-ID] PA-B1b без фильтров: весь каталог, NULL-рейтинги в конце."""
    wines, total = service.find_wines(CatalogFilters(), limit=ALL)
    assert total == len(wines) > 0
    _assert_rating_desc_nulls_last(wines)


def test_find_wines_offset_pages(service: CatalogProductService) -> None:
    """[TEST-ID] PA-B1c offset: страницы подряд совпадают с полным списком."""
    f = CatalogFilters(color="Белое")
    full, total = service.find_wines(f, limit=ALL)
    p1, t1 = service.find_wines(f, limit=5, offset=0)
    p2, t2 = service.find_wines(f, limit=5, offset=5)
    assert t1 == t2 == total
    assert [w.slug for w in p1 + p2] == [w.slug for w in full[:10]]


def test_find_wines_exclude_manufacturer(service: CatalogProductService) -> None:
    """[TEST-ID] PA-B1d exclude_manufacturer убирает все вина этого производителя."""
    winner = _winner_with_rivals(service)
    mfr = winner.manufacturer
    base = CatalogFilters(color="Красное")
    _, total = service.find_wines(base, limit=1)
    wines, excl_total = service.find_wines(
        base.model_copy(update={"exclude_manufacturer": mfr}), limit=ALL
    )
    same_mfr = _count(service, category_name="Красное", manufacturer=mfr)
    assert same_mfr >= 2
    assert excl_total == total - same_mfr
    assert all(w.manufacturer != mfr for w in wines)


def test_find_wines_exclude_slugs(service: CatalogProductService) -> None:
    """[TEST-ID] PA-B1e exclude_slugs убирает ровно указанные slug."""
    base = CatalogFilters(color="Красное")
    top, total = service.find_wines(base, limit=3)
    excluded = [w.slug for w in top[:2]]
    wines, excl_total = service.find_wines(
        base.model_copy(update={"exclude_slugs": excluded}), limit=ALL
    )
    assert excl_total == total - 2
    assert not {w.slug for w in wines} & set(excluded)
    assert wines[0].slug == top[2].slug


def test_find_wines_filters_by_dictionary_values(
    service: CatalogProductService,
) -> None:
    """[TEST-ID] PA-B1f каждое значение справочника даёт ≥1 вино (фильтры не пустые)."""
    d = service.dictionaries()
    for field, values in (
        ("color", d.colors),
        ("region", d.regions),
        ("sweetness", d.sweetness),
        ("grape", d.grapes),
        ("dish", d.dishes),
    ):
        for value in values:
            _, total = service.find_wines(CatalogFilters(**{field: value}), limit=1)
            assert total > 0, f"{field}={value!r} returns 0 wines"


def test_find_wines_unknown_value_zero(service: CatalogProductService) -> None:
    """[TEST-ID] PA-B1g неизвестный цвет → пусто, total 0."""
    assert service.find_wines(CatalogFilters(color="Фиолетовое-xyz")) == ([], 0)


def test_get_wine(service: CatalogProductService) -> None:
    """[TEST-ID] PA-B1h get_wine: известный slug → карточка; неизвестный → None."""
    top, _ = service.find_wines(CatalogFilters(), limit=1)
    card = service.get_wine(top[0].slug)
    assert card == top[0]
    assert card.color in service.dictionaries().colors
    assert service.get_wine("no-such-wine-slug-xyz") is None


# --- dictionaries --------------------------------------------------------


def test_dictionaries_clean(service: CatalogProductService) -> None:
    """[TEST-ID] PA-B2 справочники: непустые, без дублей и пустых строк."""
    d = service.dictionaries()
    for name in ("colors", "grapes", "regions", "sweetness", "dishes"):
        values: list[str] = getattr(d, name)
        assert values, f"{name} empty"
        assert all(v and v.strip() == v for v in values), f"{name}: empty/untrimmed"
        assert len(set(values)) == len(values), f"{name}: exact duplicates"
        keys = [value_key(v) for v in values]
        assert len(set(keys)) == len(keys), f"{name}: case/ё duplicates"
    assert all("," not in g and ";" not in g and "/" not in g for g in d.grapes)
    assert set(d.colors) <= {"Красное", "Белое", "Розовое", "Оранжевое"}


# --- analogs -------------------------------------------------------------


def test_analogs_for_found_winner_filters(
    service: CatalogProductService, queries_dir: Path
) -> None:
    """[TEST-ID] PA-B3 found → winner_filters: без победителя и его производителя."""
    winner = _winner_with_rivals(service)
    result = make_result(status="found", winner=winner)
    store_result(queries_dir, result)

    analogs = service.analogs_for(result.search_id, limit=5)
    assert analogs.source == "winner_filters"
    assert analogs.filters.exclude_manufacturer == winner.manufacturer
    assert winner.slug in analogs.filters.exclude_slugs
    assert analogs.filters.color == winner.color
    assert 0 < len(analogs.wines) <= 5
    assert analogs.total >= len(analogs.wines)
    _assert_rating_desc_nulls_last(analogs.wines)

    # Whole analog set (not only the first page) must respect the filters.
    all_wines, all_total = service.find_wines(analogs.filters, limit=ALL)
    assert all_total == analogs.total
    assert [w.slug for w in all_wines[:5]] == [w.slug for w in analogs.wines]
    assert all(w.manufacturer != winner.manufacturer for w in all_wines)
    assert winner.slug not in {w.slug for w in all_wines}
    assert all(w.color == winner.color for w in all_wines)


def test_analogs_for_unknown_search(service: CatalogProductService) -> None:
    """[TEST-ID] PA-B3b неизвестный search_id → SearchNotFoundError."""
    with pytest.raises(SearchNotFoundError):
        service.analogs_for("0" * 32)
    with pytest.raises(SearchNotFoundError):
        service.analogs_for("../../etc/passwd")


def _candidates(service: CatalogProductService, n: int = 5) -> list[Candidate]:
    wines, _ = service.find_wines(CatalogFilters(color="Белое"), limit=n)
    return [
        Candidate(
            rank=i,
            slug=w.slug,
            title=w.title,
            manufacturer=w.manufacturer,
            image_url=w.image_url,
            score=0.6 - i * 0.01,
        )
        for i, w in enumerate(wines, start=1)
    ]


def test_analogs_ocr_filters_color_and_grape(
    service: CatalogProductService, queries_dir: Path
) -> None:
    """[TEST-ID] PA-B4 low + OCR цвет/сорт → ocr_filters, победитель исключён."""
    cands = _candidates(service)
    winner = service.get_wine(cands[0].slug)
    grape = "Шардоне"
    if grape not in service.dictionaries().grapes:
        pytest.skip("«Шардоне» not in grape dictionary")
    hints = OcrHints(color="Белое", grapes=[grape], ocr_ran=True)
    result = make_result(status="low", winner=winner, candidates=cands, hints=hints)
    store_result(queries_dir, result)

    analogs = service.analogs_for(result.search_id)
    assert analogs.source == "ocr_filters"
    assert analogs.filters.color == "Белое"
    assert analogs.filters.grape == grape
    assert analogs.filters.exclude_slugs == [winner.slug]
    assert analogs.hints == hints
    assert winner.slug not in {w.slug for w in analogs.wines}
    assert all(w.color == "Белое" for w in analogs.wines)
    assert all(grape.lower() in w.grape_variety.lower() for w in analogs.wines)
    _assert_rating_desc_nulls_last(analogs.wines)


def test_analogs_fallback_impossible_grape_to_color(
    service: CatalogProductService, queries_dir: Path
) -> None:
    """[TEST-ID] PA-B5 невозможный сорт → повтор только с цветом (grape=None)."""
    cands = _candidates(service)
    hints = OcrHints(color="Красное", grapes=["Несуществующий Сорт Xyz"], ocr_ran=True)
    result = make_result(status="not_found", candidates=cands, hints=hints)
    store_result(queries_dir, result)

    analogs = service.analogs_for(result.search_id)
    assert analogs.source == "ocr_filters"
    assert analogs.filters.grape is None
    assert analogs.filters.color == "Красное"
    assert analogs.filters.exclude_slugs == []  # not_found: no winner to exclude
    _, red_total = service.find_wines(CatalogFilters(color="Красное"), limit=1)
    assert analogs.total == red_total
    assert len(analogs.wines) == 5


def test_analogs_fallback_impossible_color_to_vector(
    service: CatalogProductService, queries_dir: Path
) -> None:
    """[TEST-ID] PA-B5b невозможные цвет+сорт → vector: кандидаты rank 2..K."""
    cands = _candidates(service)
    hints = OcrHints(color="Фиолетовое", grapes=["Несуществующий Сорт"], ocr_ran=True)
    winner = service.get_wine(cands[0].slug)
    result = make_result(status="low", winner=winner, candidates=cands, hints=hints)
    store_result(queries_dir, result)

    analogs = service.analogs_for(result.search_id, limit=5)
    assert analogs.source == "vector"
    assert analogs.filters == CatalogFilters()
    assert analogs.hints == hints
    assert [w.slug for w in analogs.wines] == [c.slug for c in cands[1:]]
    assert analogs.total == len(cands) - 1


def test_analogs_no_hints_vector(
    service: CatalogProductService, queries_dir: Path
) -> None:
    """[TEST-ID] PA-B5c нет подсказок → vector; limit обрезает список."""
    cands = _candidates(service)
    result = make_result(status="not_found", candidates=cands, hints=OcrHints())
    store_result(queries_dir, result)
    analogs = service.analogs_for(result.search_id, limit=2)
    assert analogs.source == "vector"
    assert [w.slug for w in analogs.wines] == [c.slug for c in cands[1:3]]


def test_analogs_winner_fallback_chain(
    service: CatalogProductService, queries_dir: Path
) -> None:
    """[TEST-ID] PA-B5d found, фильтры победителя дают 0 → vector."""
    cands = _candidates(service)
    base = service.get_wine(cands[0].slug)
    assert base is not None
    ghost = base.model_copy(
        update={"slug": base.slug, "color": "Фиолетовое", "grape_variety": "Xyz"}
    )
    result = make_result(status="found", winner=ghost, candidates=cands)
    store_result(queries_dir, result)
    analogs = service.analogs_for(result.search_id)
    assert analogs.source == "vector"
    assert [w.slug for w in analogs.wines] == [c.slug for c in cands[1:]]
