"""FIX-WEB-02: «Найти в магазинах рядом» — demo map dialog on the result page."""

from __future__ import annotations

from fastapi.testclient import TestClient
from web_helpers import assert_html_page, do_search

from web.templating import STATIC_DIR

SCRIPT_URL = "/ui-static/js/shops_map.js"


def test_result_page_has_shops_dialog_and_script(client: TestClient) -> None:
    """Found result → shops block opens a native <dialog>; module script is served."""
    search_id = do_search(client, "found.jpg")
    page = assert_html_page(client.get(f"/result/{search_id}"), 200)

    triggers = [n for n in page.find_all("button") if "data-shops-open" in n.attrs]
    assert len(triggers) == 1
    assert triggers[0].get("aria-controls") == "shops-dialog"
    assert page.has("dialog", id="shops-dialog")
    assert page.find_all("script", src=SCRIPT_URL)[0].get("type") == "module"
    assert "Демо — цены и магазины случайные" in page.text
    assert "Для демо-карты нужен JavaScript." in page.text
    attribution = [
        a
        for a in page.find_all("a")
        if a.get("href") == "https://www.openstreetmap.org/copyright"
    ]
    assert len(attribution) == 1
    assert set((attribution[0].get("rel") or "").split()) >= {"noopener", "noreferrer"}

    response = client.get(SCRIPT_URL)
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]


def test_other_stubs_unchanged(client: TestClient) -> None:
    """«Цифровой сомелье» and «Чат» stay «Скоро» stubs."""
    search_id = do_search(client, "found.jpg")
    page = assert_html_page(client.get(f"/result/{search_id}"), 200)
    assert "Цифровой сомелье" in page.text
    assert "Чат" in page.text
    assert len([n for n in page.find_all("button") if "data-soon" in n.attrs]) == 2


def test_shops_map_js_builds_dom_without_inner_html() -> None:
    """DOM built via createElement/textContent; only the approved tile host."""
    text = (STATIC_DIR / "js" / "shops_map.js").read_text(encoding="utf-8")
    assert "innerHTML" not in text
    assert "insertAdjacentHTML" not in text
    assert "https://tile.openstreetmap.org" in text
