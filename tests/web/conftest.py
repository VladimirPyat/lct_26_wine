"""Fixtures for WEB-UI tests: test app (web_router + /ui-static) on a stub service."""

from __future__ import annotations

import os

# Must be set before ``web.templating`` builds the Jinja environment (StrictUndefined).
os.environ["VINE_WEB_STRICT"] = "1"

from collections.abc import Callable  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from jinja2 import StrictUndefined  # noqa: E402
from web_helpers import build_app  # noqa: E402

from core.config import ProductSettings, load_product_settings  # noqa: E402
from core.product import ProductService, StubProductService  # noqa: E402
from web.templating import templates  # noqa: E402


@pytest.fixture(autouse=True)
def _strict_templates(monkeypatch: pytest.MonkeyPatch) -> None:
    """StrictUndefined even if ``web`` was imported before this conftest."""
    monkeypatch.setenv("VINE_WEB_STRICT", "1")
    monkeypatch.setattr(templates.env, "undefined", StrictUndefined)


@pytest.fixture
def stub() -> StubProductService:
    return StubProductService()


@pytest.fixture
def make_client() -> Callable[..., TestClient]:
    def _make(
        service: ProductService, settings: ProductSettings | None = None
    ) -> TestClient:
        return TestClient(build_app(service, settings), raise_server_exceptions=False)

    return _make


@pytest.fixture
def client(
    stub: StubProductService, make_client: Callable[..., TestClient]
) -> TestClient:
    return make_client(stub)


@pytest.fixture
def product_settings() -> ProductSettings:
    return load_product_settings()
