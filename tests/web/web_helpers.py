"""Helpers for WEB-UI tests: test app builder, fake services, tiny HTML parser."""

from __future__ import annotations

import re
from collections.abc import Iterable
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient

from core.config import ProductSettings, load_product_settings
from core.product import (
    AnalogsResult,
    CatalogFilters,
    Dictionaries,
    FeedbackIn,
    ProductService,
    SearchResult,
    StubProductService,
    WineCard,
)
from web import STATIC_DIR
from web import router as web_router

JPEG_BYTES = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    + b"\x00" * 64
    + b"\xff\xd9"
)
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
SEARCH_ID_RE = re.compile(r"^/result/([0-9a-f]{32})$")
UNKNOWN_ID = "0123456789abcdef0123456789abcdef"


def build_app(
    service: ProductService, settings: ProductSettings | None = None
) -> FastAPI:
    """Minimal app: UI router + static mount; no lifespan (no models / DB)."""
    app = FastAPI()
    app.mount("/ui-static", StaticFiles(directory=str(STATIC_DIR)), name="ui_static")
    app.include_router(web_router)
    app.state.product_service = service
    app.state.product_settings = settings or load_product_settings()
    return app


def make_wine(slug: str, **overrides: Any) -> WineCard:
    """Fixture wine card (red Cabernet from Kuban by default)."""
    data: dict[str, Any] = {
        "slug": slug,
        "title": f"Вино {slug}",
        "manufacturer": f"Винодельня {slug}",
        "color": "Красное",
        "shade": "Рубиновый",
        "region": "Кубань",
        "grape_variety": "Каберне Совиньон",
        "sweetness": "сухое",
        "description": "Описание.",
        "public_rating": 4.0,
        "product_url": f"https://vino-svoe.ru/wines/{slug}",
        "image_url": f"/static/wines/{slug}.webp",
        "dishes": ["Сыры"],
        "alcohol_pct": 13.0,
        "serving_temperature": "16-18°C",
    }
    data.update(overrides)
    return WineCard(**data)


class FixtureStub(StubProductService):
    """Stub with a custom wine list (winner of any search = first wine)."""

    def __init__(self, wines: list[WineCard]) -> None:
        super().__init__()
        self._wines = list(wines)
        self._by_slug = {wine.slug: wine for wine in self._wines}


class SpyService:
    """Wraps a service and records every method call name."""

    def __init__(self, inner: ProductService) -> None:
        self.inner = inner
        self.calls: list[str] = []

    def search(
        self, image_path: Path, *, original_name: str | None = None
    ) -> SearchResult:
        self.calls.append("search")
        return self.inner.search(image_path, original_name=original_name)

    def get_search(self, search_id: str) -> SearchResult | None:
        self.calls.append("get_search")
        return self.inner.get_search(search_id)

    def query_photo_path(self, search_id: str) -> Path | None:
        self.calls.append("query_photo_path")
        return self.inner.query_photo_path(search_id)

    def analogs_for(self, search_id: str, *, limit: int = 5) -> AnalogsResult:
        self.calls.append("analogs_for")
        return self.inner.analogs_for(search_id, limit=limit)

    def get_wine(self, slug: str) -> WineCard | None:
        self.calls.append("get_wine")
        return self.inner.get_wine(slug)

    def find_wines(
        self, filters: CatalogFilters, *, limit: int = 5, offset: int = 0
    ) -> tuple[list[WineCard], int]:
        self.calls.append("find_wines")
        return self.inner.find_wines(filters, limit=limit, offset=offset)

    def dictionaries(self) -> Dictionaries:
        self.calls.append("dictionaries")
        return self.inner.dictionaries()

    def record_feedback(self, feedback: FeedbackIn) -> None:
        self.calls.append("record_feedback")
        self.inner.record_feedback(feedback)


class Node:
    """Parsed HTML start tag (flat list, attributes only)."""

    def __init__(self, tag: str, attrs: dict[str, str | None]) -> None:
        self.tag = tag
        self.attrs = attrs

    @property
    def classes(self) -> list[str]:
        return (self.attrs.get("class") or "").split()

    def get(self, name: str) -> str | None:
        return self.attrs.get(name)


class _Collector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.nodes: list[Node] = []
        self.text_parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.nodes.append(Node(tag, dict(attrs)))
        if tag in ("script", "style"):
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.text_parts.append(data)


class Page:
    """Parsed HTML page: elements + normalized visible text."""

    def __init__(self, html: str) -> None:
        collector = _Collector()
        collector.feed(html)
        collector.close()
        self.html = html
        self.nodes = collector.nodes
        self.text = " ".join(" ".join(collector.text_parts).split())

    def find_all(
        self, tag: str | None = None, *, cls: str | None = None, **attrs: str
    ) -> list[Node]:
        found: list[Node] = []
        for node in self.nodes:
            if tag is not None and node.tag != tag:
                continue
            if cls is not None and cls not in node.classes:
                continue
            if any(node.get(k.replace("_", "-")) != v for k, v in attrs.items()):
                continue
            found.append(node)
        return found

    def has(
        self, tag: str | None = None, *, cls: str | None = None, **attrs: str
    ) -> bool:
        return bool(self.find_all(tag, cls=cls, **attrs))

    def links(self) -> list[str]:
        return [n.get("href") or "" for n in self.nodes if n.tag == "a"]

    def asset_urls(self) -> Iterable[str]:
        keys = (
            "href",
            "src",
            "data-placeholder-src",
            "data-src-empty",
            "data-src-full",
        )
        for node in self.nodes:
            for key in keys:
                value = node.get(key)
                if value:
                    yield value


def assert_html_page(response: Any, status: int) -> Page:
    """Status + text/html + no traceback; returns parsed page."""
    assert response.status_code == status, response.text[:500]
    assert response.headers["content-type"].startswith("text/html")
    assert "Traceback" not in response.text
    assert 'File "' not in response.text
    return Page(response.text)


def upload(
    client: TestClient,
    name: str = "bottle.jpg",
    data: bytes = JPEG_BYTES,
    content_type: str = "image/jpeg",
) -> Any:
    return client.post(
        "/search",
        files={"image": (name, data, content_type)},
        follow_redirects=False,
    )


def do_search(client: TestClient, name: str = "bottle.jpg") -> str:
    """POST /search and return the new search_id from the 303 Location."""
    response = upload(client, name)
    assert response.status_code == 303, response.text[:500]
    match = SEARCH_ID_RE.match(response.headers["location"])
    assert match, response.headers["location"]
    return match.group(1)
