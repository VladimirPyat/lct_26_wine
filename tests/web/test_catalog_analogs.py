"""WEB-UI §C: catalog filters / chips / pagination / empty state; analogs block."""

from __future__ import annotations

from collections.abc import Callable
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient
from web_helpers import (
    FixtureStub,
    Page,
    SpyService,
    assert_html_page,
    do_search,
    make_wine,
)

from core.product import (
    AnalogsResult,
    CatalogFilters,
    OcrHints,
    StubProductService,
)


def _query(url: str) -> dict[str, list[str]]:
    parts = urlsplit(url)
    assert parts.path == "/catalog", url
    return parse_qs(parts.query)


def _chip_hrefs(page: Page) -> list[str]:
    """Hrefs of removable filter chips, in page order."""
    return [n.get("href") or "" for n in page.find_all("a", cls="chip--removable")]


def _tile_titles(page_html: str) -> list[str]:
    """Titles of wine tiles (h3.tile__title) in order."""
    titles: list[str] = []
    marker = '<h3 class="tile__title">'
    rest = page_html
    while marker in rest:
        rest = rest.split(marker, 1)[1]
        titles.append(rest.split("</h3>", 1)[0].strip())
    return titles


def _red_stub(count: int) -> FixtureStub:
    """``count`` red Cabernet wines, distinct producers, descending ratings."""
    wines = [
        make_wine(f"red-{i:02d}", public_rating=round(5.0 - i * 0.05, 2))
        for i in range(count)
    ]
    return FixtureStub(wines)


# --- C-1 catalog -----------------------------------------------------------------


def test_c1_filters_reflected_as_chips(client: TestClient) -> None:
    """[C-1] query filters → chips; each chip link removes exactly that filter."""
    page = assert_html_page(client.get("/catalog?color=Красное&region=Кубань"), 200)
    hrefs = _chip_hrefs(page)
    assert len(hrefs) == 2
    queries = [_query(h) for h in hrefs]
    assert {"region": ["Кубань"]} in queries
    assert {"color": ["Красное"]} in queries
    assert "Красное" in page.text and "Кубань" in page.text
    assert "Сбросить все" in page.text
    assert "Найдено: 2" in page.text
    titles = _tile_titles(page.html)
    assert titles == ["Abrau Estates красное", "101 оттенок красного. Каберне"]


def test_c1_selected_options_reflect_filters(client: TestClient) -> None:
    """[C-1] filter form preselects values from query."""
    page = assert_html_page(client.get("/catalog?color=Белое&sweetness=сухое"), 200)
    selected = {
        (n.get("value") or "") for n in page.find_all("option") if "selected" in n.attrs
    }
    assert {"Белое", "сухое"} <= selected


def test_c1_all_filter_kinds_have_removable_chips(client: TestClient) -> None:
    """[C-1] every CatalogFilters field → its own chip; removal keeps the others."""
    params = {
        "color": "Красное",
        "grape": "Каберне Совиньон",
        "region": "Кубань",
        "sweetness": "сухое",
        "dish": "Сыры",
        "exclude_manufacturer": "Абрау-Дюрсо",
    }
    response = client.get(
        "/catalog",
        params=[*params.items(), ("exclude_slugs", "some-slug")],
    )
    page = assert_html_page(response, 200)
    hrefs = _chip_hrefs(page)
    assert len(hrefs) == len(params) + 1
    full = {k: [v] for k, v in params.items()} | {"exclude_slugs": ["some-slug"]}
    removed_keys = []
    for href in hrefs:
        query = _query(href)
        missing = set(full) - set(query)
        assert len(missing) == 1, (href, missing)
        key = missing.pop()
        removed_keys.append(key)
        assert query == {k: v for k, v in full.items() if k != key}
    assert sorted(removed_keys) == sorted(full)
    assert "Кроме винодельни: Абрау-Дюрсо" in page.text
    assert "К блюду: Сыры" in page.text
    assert "101 оттенок красного. Каберне" in page.text
    assert "Abrau Estates красное" not in page.text


def test_c1_catalog_sorted_by_rating(client: TestClient) -> None:
    """[C-1] results sorted by public_rating desc, unrated last."""
    page = assert_html_page(client.get("/catalog"), 200)
    assert _tile_titles(page.html) == [
        "Abrau Estates красное",
        "Cantiani Aligote Riesling",
        "101 оттенок красного. Каберне",
        "Adagum Estate Rose",
        "4 elements. Совиньон Блан",
    ]
    assert not page.has("nav", cls="pagination")


def test_c1_pagination_links(make_client: Callable[..., TestClient]) -> None:
    """[C-1] 45 wines / 20 per page → 3 pages; prev/next/current; filters preserved."""
    client = make_client(_red_stub(45))

    first = assert_html_page(client.get("/catalog?color=Красное"), 200)
    assert len(_tile_titles(first.html)) == 20
    assert "Найдено: 45" in first.text
    assert first.has("nav", cls="pagination")
    page_links = [h for h in first.links() if h.startswith("/catalog") and "page=" in h]
    assert any(_query(h).get("page") == ["2"] for h in page_links)
    assert any(_query(h).get("page") == ["3"] for h in page_links)
    for href in page_links:
        assert _query(href)["color"] == ["Красное"]
    assert not first.has("a", rel="prev")
    nxt = first.find_all("a", rel="next")
    assert nxt and _query(nxt[0].get("href") or "")["page"] == ["2"]
    current = first.find_all(cls="pagination__link--current")
    assert current and current[0].get("aria-current") == "page"

    second = assert_html_page(client.get("/catalog?color=Красное&page=2"), 200)
    titles_2 = _tile_titles(second.html)
    assert len(titles_2) == 20
    assert set(titles_2).isdisjoint(_tile_titles(first.html))
    prev = second.find_all("a", rel="prev")
    assert prev and "page" not in _query(prev[0].get("href") or "")
    assert _query(second.find_all("a", rel="next")[0].get("href") or "")["page"] == [
        "3"
    ]

    third = assert_html_page(client.get("/catalog?color=Красное&page=3"), 200)
    assert len(_tile_titles(third.html)) == 5
    assert not third.has("a", rel="next")


@pytest.mark.parametrize("raw_page", ["abc", "-1", "0", "99999999"])
def test_c1_bad_page_param_is_tolerated(
    make_client: Callable[..., TestClient], raw_page: str
) -> None:
    """[C-1] bad / out-of-range page → 200, not an error page."""
    client = make_client(_red_stub(25))
    page = assert_html_page(client.get(f"/catalog?page={raw_page}"), 200)
    assert _tile_titles(page.html)


def test_c1_empty_state(client: TestClient) -> None:
    """[C-1] no matches → empty-state text + reset link; chips still shown."""
    page = assert_html_page(client.get("/catalog?color=Оранжевое"), 200)
    assert "По этим фильтрам вин не нашлось." in page.text
    assert "Сбросить фильтры" in page.text
    assert "/catalog" in page.links()
    assert _chip_hrefs(page) == ["/catalog"]
    assert _tile_titles(page.html) == []


# --- C-2 analogs -----------------------------------------------------------------


def test_c2_low_analogs_capped_with_show_all(
    make_client: Callable[..., TestClient],
) -> None:
    """[C-2] total > 5 → 5 cards + «Показать все (N)» → /catalog with same filters."""
    stub = _red_stub(8)
    client = make_client(stub)
    search_id = do_search(client, "x_low.jpg")
    result = stub.get_search(search_id)
    assert result is not None and result.analogs is not None
    assert result.analogs.total == 7

    page = assert_html_page(client.get(f"/result/{search_id}"), 200)
    section = page.html.split('id="analogs"', 1)[1]
    assert len(_tile_titles(section)) == 5
    assert "Показать все (7)" in page.text
    show_all = [
        n.get("href") or ""
        for n in page.find_all("a", cls="btn")
        if (n.get("href") or "").startswith("/catalog?")
    ]
    assert show_all
    query = _query(show_all[0])
    assert query["color"] == ["Красное"]
    assert query["grape"] == ["Каберне Совиньон"]
    assert query["exclude_slugs"] == ["red-00"]


def test_c2_found_analogs_param_capped(make_client: Callable[..., TestClient]) -> None:
    """[C-2] ?analogs=1 on found (winner_filters) → ≤5 cards + «Показать все (7)»."""
    stub = _red_stub(8)
    spy = SpyService(stub)
    client = make_client(spy)
    search_id = do_search(client, "found.jpg")
    page = assert_html_page(client.get(f"/result/{search_id}?analogs=1"), 200)
    assert "Аналоги от других виноделен" in page.text
    section = page.html.split('id="analogs"', 1)[1]
    assert len(_tile_titles(section)) == 5
    assert "Показать все (7)" in page.text
    assert "analogs_for" in spy.calls


def test_c2_no_show_all_when_total_le_5(client: TestClient) -> None:
    """[C-2] total ≤ 5 → no «Показать все»."""
    search_id = do_search(client, "x_notfound.jpg")
    page = assert_html_page(client.get(f"/result/{search_id}"), 200)
    assert "Показать все" not in page.text
    section = page.html.split('id="analogs"', 1)[1]
    assert 1 <= len(_tile_titles(section)) <= 5


def test_c2_analog_chips_remove_one_filter(client: TestClient) -> None:
    """[C-2] analogs filter chips link to /catalog with that filter removed."""
    search_id = do_search(client, "x_notfound.jpg")
    page = assert_html_page(client.get(f"/result/{search_id}"), 200)
    hrefs = _chip_hrefs(page)
    queries = [_query(h) for h in hrefs]
    assert {"grape": ["Каберне Совиньон"]} in queries
    assert {"color": ["Красное"]} in queries


def test_c2_empty_analogs(make_client: Callable[..., TestClient]) -> None:
    """[C-2] empty analogs → «Аналог подобрать не удалось» + link to catalog."""
    whites = [
        make_wine(f"white-{i}", color="Белое", grape_variety="Шардоне")
        for i in range(3)
    ]
    client = make_client(FixtureStub(whites))
    search_id = do_search(client, "x_notfound.jpg")
    page = assert_html_page(client.get(f"/result/{search_id}"), 200)
    assert "Аналог подобрать не удалось" in page.text
    assert "/catalog" in page.links()
    assert "Показать все" not in page.text


def test_c2_vector_source_title(make_client: Callable[..., TestClient]) -> None:
    """[C-2] source=vector → «Похожие по виду»."""
    wines = [make_wine("red-winner")] + [
        make_wine(f"white-{i}", color="Белое", grape_variety="Шардоне")
        for i in range(3)
    ]
    client = make_client(FixtureStub(wines))
    search_id = do_search(client, "found.jpg")
    page = assert_html_page(client.get(f"/result/{search_id}?analogs=1"), 200)
    assert "Похожие по виду" in page.text


class _OverLimitAnalogs(StubProductService):
    """Service ignoring ``limit``: returns 7 analog wines (UI must still show ≤5)."""

    def analogs_for(self, search_id: str, *, limit: int = 5) -> AnalogsResult:
        wines = [make_wine(f"extra-{i}") for i in range(7)]
        return AnalogsResult(
            source="winner_filters",
            filters=CatalogFilters(color="Красное"),
            hints=OcrHints(),
            wines=wines,
            total=12,
        )


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG-WEB-01: views.build_analogs_view passes analogs.wines through uncapped; "
        "contract web_ui.md §3 says the analogs block shows ≤5 cards"
    ),
)
def test_c2_ui_caps_cards_even_if_service_returns_more(
    make_client: Callable[..., TestClient],
) -> None:
    """[C-2] contract §3: analogs block shows ≤5 cards."""
    client = make_client(_OverLimitAnalogs())
    search_id = do_search(client, "found.jpg")
    page = assert_html_page(client.get(f"/result/{search_id}?analogs=1"), 200)
    section = page.html.split('id="analogs"', 1)[1]
    assert len(_tile_titles(section)) <= 5
    assert "Показать все (12)" in page.text
