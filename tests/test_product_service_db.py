"""PROD-API B — CatalogProductService на Compose Postgres (read-only, без моделей)."""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Iterator
from pathlib import Path

import pytest

from core.config import load_product_settings
from core.product import catalog_service as catalog_mod
from core.product.catalog_service import CatalogProductService
from core.product.schemas import Candidate, CatalogFilters, OcrHints, WineCard
from core.product.service import SearchNotFoundError
from core.product.vocabulary import split_grapes, value_key
from db.repository import WineRepository
from db.session import session_scope
from product_helpers import build_db_service, make_result, make_settings, store_result

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


def _canonical_grape(service: CatalogProductService, raw: str) -> str | None:
    """Значение справочника сортов для произвольного написания (или None)."""
    key = value_key(raw)
    return next((g for g in service.dictionaries().grapes if value_key(g) == key), None)


def _has_grape(wine: WineCard, grape: str) -> bool:
    """Сорт — целый элемент ``grape_variety`` (не подстрока)."""
    key = value_key(grape)
    return any(value_key(part) == key for part in split_grapes(wine.grape_variety))


def _winner_with_grape_rivals(service: CatalogProductService) -> tuple[WineCard, str]:
    """Вино, чей первый сорт есть у ≥6 вин других производителей."""
    wines, _ = service.find_wines(CatalogFilters(color="Красное"), limit=ALL)
    for wine in wines:
        parts = split_grapes(wine.grape_variety)
        grape = _canonical_grape(service, parts[0]) if parts else None
        if grape is None:
            continue
        _, rivals = service.find_wines(
            CatalogFilters(grape=grape, exclude_manufacturer=wine.manufacturer),
            limit=1,
        )
        if rivals > 5:
            return wine, grape
    pytest.skip("no red wine whose grape has >5 wines of other manufacturers")


class _DbSpy:
    """Счётчик вызовов count_filters / search_filters (проверка «без запроса в БД»)."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.calls: list[str] = []
        for name in ("count_filters", "search_filters"):
            original = getattr(WineRepository, name)
            monkeypatch.setattr(WineRepository, name, self._wrap(name, original))

    def _wrap(self, name: str, original):  # noqa: ANN001, ANN202
        def spy(repo, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003, ANN202
            self.calls.append(name)
            return original(repo, *args, **kwargs)

        return spy


def _forbid_ocr(
    service: CatalogProductService, monkeypatch: pytest.MonkeyPatch
) -> list[str]:
    """Любой вызов OCR (runtime.get_ocr / recognize_crop) записывается и падает."""
    calls: list[str] = []

    def boom(*_args: object, **_kwargs: object) -> None:
        calls.append("ocr")
        msg = "OCR must not be called for found analogs"
        raise AssertionError(msg)

    monkeypatch.setattr(service._runtime, "get_ocr", boom, raising=False)
    monkeypatch.setattr(catalog_mod, "recognize_crop", boom)
    return calls


def test_analogs_for_found_winner_filters(
    service: CatalogProductService, queries_dir: Path
) -> None:
    """[TEST-ID] PA-B3-fix1 found → winner_filters: первый сорт, без цвета.

    Другие производители, победитель исключён, hints = цвет/сорт победителя.
    """
    winner, grape = _winner_with_grape_rivals(service)
    result = make_result(status="found", winner=winner)
    store_result(queries_dir, result)

    analogs = service.analogs_for(result.search_id, limit=5)
    assert analogs.source == "winner_filters"
    assert analogs.filters.color is None
    assert analogs.filters.region is None
    assert analogs.filters.grape == grape
    assert analogs.filters.exclude_manufacturer == winner.manufacturer
    assert analogs.filters.exclude_slugs == [winner.slug]
    assert analogs.hints.color == winner.color
    assert analogs.hints.grapes == [grape]
    assert analogs.hints.manufacturer is None
    assert analogs.hints.ocr_ran is False
    assert len(analogs.wines) == 5
    _assert_rating_desc_nulls_last(analogs.wines)

    # Whole analog set (not only the first page) must respect the filters.
    all_wines, all_total = service.find_wines(analogs.filters, limit=ALL)
    assert all_total == analogs.total == len(all_wines)
    assert [w.slug for w in all_wines[:5]] == [w.slug for w in analogs.wines]
    assert all(_has_grape(w, grape) for w in all_wines)
    assert all(w.manufacturer != winner.manufacturer for w in all_wines)
    assert winner.slug not in {w.slug for w in all_wines}


def test_analogs_found_makes_no_ocr_call(
    service: CatalogProductService,
    queries_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """[TEST-ID] PA-B3c-fix1 found → analogs_for без единого вызова OCR."""
    winner, grape = _winner_with_grape_rivals(service)
    calls = _forbid_ocr(service, monkeypatch)
    result = make_result(status="found", winner=winner)
    store_result(queries_dir, result)

    analogs = service.analogs_for(result.search_id, limit=5)
    assert calls == []
    assert analogs.source == "winner_filters"
    assert analogs.filters.grape == grape
    assert analogs.filters.color is None
    assert analogs.hints.ocr_ran is False


def test_analogs_found_blend_uses_first_grape(
    service: CatalogProductService, queries_dir: Path
) -> None:
    """[TEST-ID] PA-B3d-fix1 бленд («A, B» / «A/B») → фильтр по первому сорту."""
    wines, _ = service.find_wines(CatalogFilters(), limit=ALL)
    blend: WineCard | None = None
    first: str | None = None
    for wine in wines:
        if not any(sep in wine.grape_variety for sep in (",", "/")):
            continue
        parts = split_grapes(wine.grape_variety)
        if len(parts) < 2:
            continue
        first = _canonical_grape(service, parts[0])
        if first is not None and value_key(parts[1]) != value_key(parts[0]):
            blend = wine
            break
    if blend is None or first is None:
        pytest.skip("no blend wine with a dictionary first grape")
    second = _canonical_grape(service, split_grapes(blend.grape_variety)[1])

    result = make_result(status="found", winner=blend)
    store_result(queries_dir, result)
    analogs = service.analogs_for(result.search_id, limit=5)
    assert analogs.source == "winner_filters"
    assert analogs.filters.grape == first
    assert analogs.filters.grape != second
    assert analogs.hints.grapes == [first]
    all_wines, all_total = service.find_wines(analogs.filters, limit=ALL)
    assert all_total == analogs.total
    assert all(_has_grape(w, first) for w in all_wines)
    assert all(w.manufacturer != blend.manufacturer for w in all_wines)


def test_analogs_limit_and_total(
    service: CatalogProductService, queries_dir: Path
) -> None:
    """[TEST-ID] PA-B3e-fix1 limit/total: total = полный find_wines, порядок совпадает.
    """
    winner, _grape = _winner_with_grape_rivals(service)
    result = make_result(status="found", winner=winner)
    store_result(queries_dir, result)
    for limit in (1, 2, 5):
        analogs = service.analogs_for(result.search_id, limit=limit)
        full, full_total = service.find_wines(analogs.filters, limit=ALL)
        assert analogs.total == full_total
        assert len(analogs.wines) == min(limit, full_total)
        assert [w.slug for w in analogs.wines] == [w.slug for w in full[:limit]]
        _assert_rating_desc_nulls_last(full)


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


def test_analogs_ocr_filters_grape_only(
    service: CatalogProductService, queries_dir: Path
) -> None:
    """[TEST-ID] PA-B4-fix1 low + OCR цвет/сорт → ocr_filters только по сорту.

    Цвет из подсказок не становится фильтром; победитель исключён.
    """
    cands = _candidates(service)
    winner = service.get_wine(cands[0].slug)
    assert winner is not None
    grape = "Шардоне"
    if grape not in service.dictionaries().grapes:
        pytest.skip("«Шардоне» not in grape dictionary")
    hints = OcrHints(color="Белое", grapes=[grape], ocr_ran=True)
    result = make_result(status="low", winner=winner, candidates=cands, hints=hints)
    store_result(queries_dir, result)

    analogs = service.analogs_for(result.search_id)
    assert analogs.source == "ocr_filters"
    assert analogs.filters.color is None
    assert analogs.filters.grape == grape
    assert analogs.filters.exclude_manufacturer is None
    assert analogs.filters.exclude_slugs == [winner.slug]
    assert analogs.hints == hints
    assert analogs.wines
    assert winner.slug not in {w.slug for w in analogs.wines}
    assert all(_has_grape(w, grape) for w in analogs.wines)
    _assert_rating_desc_nulls_last(analogs.wines)

    # Color is not constrained: total equals the grape-only count.
    grape_only = CatalogFilters(grape=grape, exclude_slugs=[winner.slug])
    _, grape_total = service.find_wines(grape_only, limit=1)
    _, white_total = service.find_wines(
        grape_only.model_copy(update={"color": "Белое"}), limit=1
    )
    assert analogs.total == grape_total >= white_total


def test_analogs_impossible_grape_empty(
    service: CatalogProductService,
    queries_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """[TEST-ID] PA-B5-fix1 невозможный сорт → ocr_filters, пусто, без повтора по цвету.
    """
    cands = _candidates(service)
    impossible = "Несуществующий Сорт Xyz"
    hints = OcrHints(color="Красное", grapes=[impossible], ocr_ran=True)
    result = make_result(status="not_found", candidates=cands, hints=hints)
    store_result(queries_dir, result)

    spy = _DbSpy(monkeypatch)
    analogs = service.analogs_for(result.search_id)
    assert analogs.source == "ocr_filters"
    assert analogs.filters.grape == impossible
    assert analogs.filters.color is None
    assert analogs.filters.exclude_slugs == []  # not_found: no winner to exclude
    assert analogs.wines == []
    assert analogs.total == 0
    assert analogs.hints == hints
    # Exactly one count query, no retry, no page query for 0 matches.
    assert spy.calls == ["count_filters"]


def test_analogs_color_hint_without_grape_empty(
    service: CatalogProductService,
    queries_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """[TEST-ID] PA-B5b-fix1 только цвет, нет сорта → ocr_filters, пусто (цвет не
    фильтр).
    """
    cands = _candidates(service)
    winner = service.get_wine(cands[0].slug)
    assert winner is not None
    hints = OcrHints(color="Красное", grapes=[], ocr_ran=True)
    result = make_result(status="low", winner=winner, candidates=cands, hints=hints)
    store_result(queries_dir, result)

    spy = _DbSpy(monkeypatch)
    analogs = service.analogs_for(result.search_id, limit=5)
    assert analogs.source == "ocr_filters"
    assert analogs.filters.grape is None
    assert analogs.filters.color is None
    assert analogs.filters.exclude_slugs == [winner.slug]
    assert analogs.hints == hints
    assert analogs.wines == []
    assert analogs.total == 0
    assert spy.calls == []


def test_analogs_no_hints_empty(
    service: CatalogProductService,
    queries_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """[TEST-ID] PA-B5c-fix1 нет подсказок → ocr_filters, пусто, без запроса в БД."""
    cands = _candidates(service)
    result = make_result(status="not_found", candidates=cands, hints=OcrHints())
    store_result(queries_dir, result)
    spy = _DbSpy(monkeypatch)
    analogs = service.analogs_for(result.search_id, limit=2)
    assert analogs.source == "ocr_filters"
    assert analogs.filters.grape is None
    assert analogs.filters.exclude_slugs == []
    assert analogs.wines == []
    assert analogs.total == 0
    assert spy.calls == []


def _single_manufacturer_grape(service: CatalogProductService) -> WineCard:
    """Вино, чей первый сорт встречается только у его производителя."""
    wines, _ = service.find_wines(CatalogFilters(), limit=ALL)
    for wine in wines:
        parts = split_grapes(wine.grape_variety)
        grape = _canonical_grape(service, parts[0]) if parts else None
        if grape is None:
            continue
        _, rivals = service.find_wines(
            CatalogFilters(grape=grape, exclude_manufacturer=wine.manufacturer),
            limit=1,
        )
        if rivals == 0:
            return wine
    pytest.skip("every first grape has wines of other manufacturers")


def test_analogs_winner_no_match_or_no_grape_empty(
    service: CatalogProductService,
    queries_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """[TEST-ID] PA-B5d-fix1 found: 0 совпадений → пусто без повтора; нет сорта → без
    БД.
    """
    # (1) Winner grape exists, but only at the winner's own manufacturer.
    lonely = _single_manufacturer_grape(service)
    result = make_result(status="found", winner=lonely)
    store_result(queries_dir, result)
    spy = _DbSpy(monkeypatch)
    analogs = service.analogs_for(result.search_id)
    assert analogs.source == "winner_filters"
    assert analogs.filters.grape == _canonical_grape(
        service, split_grapes(lonely.grape_variety)[0]
    )
    assert analogs.filters.color is None
    assert analogs.wines == []
    assert analogs.total == 0
    assert spy.calls == ["count_filters"]

    # (2) Winner grape absent from the dictionary → grape None, no DB query.
    cands = _candidates(service)
    base = service.get_wine(cands[0].slug)
    assert base is not None
    ghost = base.model_copy(update={"color": "Фиолетовое", "grape_variety": "Xyz"})
    result = make_result(status="found", winner=ghost, candidates=cands)
    store_result(queries_dir, result)
    spy.calls.clear()
    analogs = service.analogs_for(result.search_id)
    assert analogs.source == "winner_filters"
    assert analogs.filters.grape is None
    assert analogs.wines == []
    assert analogs.total == 0
    assert spy.calls == []

    # (3) Winner without grape_variety → empty, no DB query.
    no_grape = base.model_copy(update={"grape_variety": ""})
    result = make_result(status="found", winner=no_grape, candidates=cands)
    store_result(queries_dir, result)
    analogs = service.analogs_for(result.search_id)
    assert analogs.source == "winner_filters"
    assert analogs.filters.grape is None
    assert analogs.filters.exclude_manufacturer == base.manufacturer
    assert analogs.filters.exclude_slugs == [base.slug]
    assert analogs.hints.grapes == []
    assert analogs.hints.ocr_ran is False
    assert analogs.wines == []
    assert analogs.total == 0
    assert spy.calls == []


# --- grape_aliases config ------------------------------------------------


def test_repo_grape_aliases_keys_in_dictionary(
    service: CatalogProductService,
) -> None:
    """[TEST-ID] PA-B6-fix1 все ключи grape_aliases из product.yaml есть в справочнике
    БД.
    """
    aliases = load_product_settings().analogs.grape_aliases
    assert aliases, "product.yaml analogs.grape_aliases is empty"
    grapes = set(service.dictionaries().grapes)
    missing = [key for key in aliases if key not in grapes]
    assert missing == [], f"grape_aliases keys not in DB dictionary: {missing}"


def test_unknown_grape_alias_key_warned_and_ignored(
    service: CatalogProductService,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """[TEST-ID] PA-B6b-fix1 неизвестный ключ grape_aliases → WARNING и игнор."""
    base = make_settings(tmp_path)
    settings = base.model_copy(
        update={
            "analogs": base.analogs.model_copy(
                update={
                    "grape_aliases": {
                        "Санджовезе": ["sangiovese"],
                        "Несуществующий Сорт Xyz": ["nonexistent grape"],
                    }
                }
            )
        }
    )
    with caplog.at_level(logging.WARNING, logger="core.product.catalog_service"):
        svc = CatalogProductService(service._runtime, settings)
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert any("Несуществующий Сорт Xyz" in r.getMessage() for r in warnings)
    assert "Несуществующий Сорт Xyz" not in svc._grape_aliases
    if "Санджовезе" in svc.dictionaries().grapes:
        assert svc._grape_aliases.get("Санджовезе") == ["sangiovese"]


def test_repo_grape_aliases_no_startup_warning(
    service: CatalogProductService,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """[TEST-ID] PA-B6c-fix1 prod grape_aliases: при старте сервиса нет WARNING."""
    base = make_settings(tmp_path)
    prod = load_product_settings().analogs.grape_aliases
    settings = base.model_copy(
        update={"analogs": base.analogs.model_copy(update={"grape_aliases": prod})}
    )
    with caplog.at_level(logging.WARNING, logger="core.product.catalog_service"):
        CatalogProductService(service._runtime, settings)
    messages = [r.getMessage() for r in caplog.records]
    assert [m for m in messages if "grape_aliases" in m] == []
