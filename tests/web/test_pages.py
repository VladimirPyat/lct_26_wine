"""WEB-UI §A: pages render (tester_web_ui.md A)."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from web_helpers import UNKNOWN_ID, Page, SpyService, assert_html_page

from core.product import StubProductService

FIXTURE_SLUG = "abrau-dyurso-abrau-estates-krasnoe-kaberne-sovinon-suhoe-13"


def _viewport(page_html: str) -> str:
    metas = Page(page_html).find_all("meta", name="viewport")
    assert len(metas) == 1, "exactly one viewport meta expected"
    return metas[0].get("content") or ""


@pytest.mark.parametrize(
    "path",
    ["/", "/catalog", "/me", f"/wine/{FIXTURE_SLUG}"],
)
def test_a1_pages_render_html_with_viewport(client: TestClient, path: str) -> None:
    """[A-1] 200, text/html, viewport meta present, zoom not disabled."""
    response = client.get(path)
    page = assert_html_page(response, 200)
    content = _viewport(response.text).replace(" ", "").lower()
    assert "width=device-width" in content
    assert "user-scalable=no" not in content
    assert "user-scalable=0" not in content
    assert "maximum-scale=1" not in content
    assert "user-scalable" not in response.text.lower()
    assert page.has("html", lang="ru")


def test_a1_scan_page_has_no_js_upload_form(client: TestClient) -> None:
    """[A-1] scanner works without JS: multipart form POST /search with file input."""
    page = assert_html_page(client.get("/"), 200)
    forms = page.find_all("form", action="/search")
    assert len(forms) == 1
    assert (forms[0].get("method") or "").lower() == "post"
    assert forms[0].get("enctype") == "multipart/form-data"
    inputs = page.find_all("input", type="file", name="image")
    assert inputs, "file input name=image missing"
    assert "Загрузить фото" in page.text


def test_a1_wine_page_shows_fixture(
    client: TestClient, stub: StubProductService
) -> None:
    """[A-1] /wine/{slug} renders the card of that wine."""
    wine = stub.get_wine(FIXTURE_SLUG)
    assert wine is not None
    page = assert_html_page(client.get(f"/wine/{FIXTURE_SLUG}"), 200)
    assert wine.title in page.text
    assert wine.manufacturer in page.text


def test_a1_nav_links_present(client: TestClient) -> None:
    """[A-1] header / tab bar link to scanner, catalog and cabinet."""
    page = assert_html_page(client.get("/catalog"), 200)
    links = page.links()
    for href in ("/", "/catalog", "/me"):
        assert href in links


@pytest.mark.parametrize("path", ["/wine/x", "/wine/no-such-wine-slug"])
def test_a2_unknown_wine_404_page(client: TestClient, path: str) -> None:
    """[A-2] unknown slug → HTML 404 page, no traceback."""
    page = assert_html_page(client.get(path), 404)
    assert "не найден" in page.text.lower()


def test_a2_unknown_result_404_page(client: TestClient) -> None:
    """[A-2] unknown 32-hex search_id → HTML 404 page."""
    page = assert_html_page(client.get(f"/result/{UNKNOWN_ID}"), 404)
    assert "не найден" in page.text.lower()


@pytest.mark.parametrize(
    "bad_id",
    ["not-hex", "0123456789ABCDEF0123456789ABCDEF", "0123456789abcdef", "z" * 32],
)
def test_a2_invalid_result_id_404_without_service_call(
    make_client: Callable[..., TestClient], bad_id: str
) -> None:
    """[A-2] non-32-hex id → 404 page, service never called."""
    spy = SpyService(StubProductService())
    client = make_client(spy)
    for path in (f"/result/{bad_id}", f"/result/{bad_id}/photo"):
        assert_html_page(client.get(path), 404)
    response = client.post(
        f"/result/{bad_id}/feedback", data={"verdict": "match"}, follow_redirects=False
    )
    assert_html_page(response, 404)
    assert spy.calls == []
