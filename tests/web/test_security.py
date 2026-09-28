"""WEB-UI §D: security / quality — escaping, unsafe URLs, templates, assets."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jinja2 import UndefinedError
from web_helpers import (
    FixtureStub,
    Page,
    assert_html_page,
    do_search,
    make_wine,
)

from core.product import StubProductService, WineCard
from web.templating import STATIC_DIR, TEMPLATES_DIR, templates

XSS = "<script>alert(1)</script>"
XSS_ESCAPED = "&lt;script&gt;alert(1)&lt;/script&gt;"
XSS_ATTR = '"><img src=x onerror=alert(1)>'
XSS_SLUG = "xss-wine"
WEB_SRC = TEMPLATES_DIR.parent
TEMPLATE_FILES = sorted(TEMPLATES_DIR.rglob("*.html"))


def _xss_stub(
    product_url: str | None = "https://vino-svoe.ru/wines/xss",
) -> FixtureStub:
    wine = make_wine(
        XSS_SLUG,
        title=XSS,
        manufacturer=XSS_ATTR,
        description=f"Описание {XSS}",
        region=XSS,
        shade=XSS_ATTR,
        grape_variety=f"Каберне Совиньон, {XSS}",
        dishes=[XSS],
        serving_temperature=XSS_ATTR,
        product_url=product_url,
    )
    # Second red Cabernet so that analogs (low / not_found) render tiles too.
    other = make_wine("xss-other", title=XSS, manufacturer=XSS_ATTR)
    return FixtureStub([wine, other])


def _assert_no_injection(html: str) -> None:
    assert XSS not in html
    assert "<img src=x" not in html
    page = Page(html)
    inline_scripts = [n for n in page.find_all("script") if not n.get("src")]
    assert inline_scripts == [], "unexpected inline <script>"
    for node in page.nodes:
        for name in node.attrs:
            assert not name.startswith("on"), (
                f"event handler attr {name} on <{node.tag}>"
            )


def _unsafe_hrefs(page: Page) -> list[str]:
    bad: list[str] = []
    for node in page.nodes:
        for key in ("href", "src", "action", "formaction"):
            value = (node.get(key) or "").strip().lower()
            if value.startswith(("javascript:", "data:text", "vbscript:")):
                bad.append(value)
    return bad


# --- D-1 escaping -----------------------------------------------------------------


def test_d1_wine_page_escapes_catalog_strings(
    make_client: Callable[..., TestClient],
) -> None:
    """[D-1] <script> title in /wine/{slug} is escaped."""
    client = make_client(_xss_stub())
    response = client.get(f"/wine/{XSS_SLUG}")
    assert_html_page(response, 200)
    assert XSS_ESCAPED in response.text
    _assert_no_injection(response.text)


@pytest.mark.parametrize(
    ("name", "query"),
    [
        ("found.jpg", ""),
        ("found.jpg", "?analogs=1"),
        ("found.jpg", "?fb=1&verdict=mismatch"),
        ("x_low.jpg", ""),
        ("x_notfound.jpg", ""),
    ],
)
def test_d1_result_page_escapes_catalog_strings(
    make_client: Callable[..., TestClient], name: str, query: str
) -> None:
    """[D-1] result page (card, data-* attrs, analogs tiles) escapes catalog strings."""
    client = make_client(_xss_stub())
    search_id = do_search(client, name)
    response = client.get(f"/result/{search_id}{query}")
    assert_html_page(response, 200)
    assert XSS_ESCAPED in response.text
    _assert_no_injection(response.text)


def test_d1_catalog_escapes_catalog_strings_and_query(
    make_client: Callable[..., TestClient],
) -> None:
    """[D-1] catalog tiles, chips, <select> escape strings (also from query)."""
    client = make_client(_xss_stub())
    for response in (
        client.get("/catalog"),
        client.get("/catalog", params={"color": XSS, "dish": XSS_ATTR}),
        client.get("/catalog", params={"exclude_manufacturer": XSS}),
    ):
        assert_html_page(response, 200)
        assert XSS_ESCAPED in response.text
        _assert_no_injection(response.text)


def test_d1_upload_filename_not_reflected_unescaped(client: TestClient) -> None:
    """[D-1] malicious upload filename does not break out anywhere."""
    response = client.post(
        "/search",
        files={"image": (f"{XSS}.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 415
    _assert_no_injection(response.text)


# --- D-2 unsafe product_url ---------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        " JavaScript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "//evil.example/x",
        "vino-svoe.ru/wines/x",
        "https://",
    ],
)
def test_d2_non_http_product_url_not_rendered(
    make_client: Callable[..., TestClient], url: str
) -> None:
    """[D-2] product_url not http(s):// → «Открыть на сайте» link hidden."""
    stub = _xss_stub(product_url=url)
    client = make_client(stub)
    search_id = do_search(client, "found.jpg")
    for path in (f"/wine/{XSS_SLUG}", f"/result/{search_id}"):
        response = client.get(path)
        page = assert_html_page(response, 200)
        assert "Открыть на сайте" not in page.text, path
        assert url.strip() not in page.links()
        assert _unsafe_hrefs(page) == [], path


def test_d2_http_product_url_rendered_safely(client: TestClient) -> None:
    """[D-2] http(s) product_url → link with rel=noopener noreferrer, target=_blank."""
    slug = "abrau-dyurso-abrau-estates-krasnoe-kaberne-sovinon-suhoe-13"
    page = assert_html_page(client.get(f"/wine/{slug}"), 200)
    links = [
        a for a in page.find_all("a") if (a.get("href") or "").startswith("https://")
    ]
    assert links
    for link in links:
        assert link.get("target") == "_blank"
        assert set((link.get("rel") or "").split()) >= {"noopener", "noreferrer"}


def test_d2_null_product_url_hidden(
    client: TestClient, stub: StubProductService
) -> None:
    """[D-2] product_url=None (fixture «Adagum Estate Rose») → no site link."""
    slug = "olymp-winery-adagum-estate-rose-kaberne-sovinon-rozovoe-suhoe-11"
    wine = stub.get_wine(slug)
    assert isinstance(wine, WineCard) and wine.product_url is None
    page = assert_html_page(client.get(f"/wine/{slug}"), 200)
    assert "Открыть на сайте" not in page.text


# --- D-3 template grep --------------------------------------------------------------


def test_d3_templates_exist() -> None:
    names = {p.relative_to(TEMPLATES_DIR).as_posix() for p in TEMPLATE_FILES}
    for required in (
        "base.html",
        "pages/scan.html",
        "pages/result.html",
        "pages/wine.html",
        "pages/catalog.html",
        "pages/me.html",
        "pages/error.html",
    ):
        assert required in names


@pytest.mark.parametrize("path", TEMPLATE_FILES, ids=lambda p: p.name)
def test_d3_no_safe_filter(path: Path) -> None:
    """[D-3] no ``|safe`` in templates."""
    text = path.read_text(encoding="utf-8")
    assert not re.search(r"\|\s*safe\b", text)
    assert not re.search(r"autoescape\s+false", text, re.IGNORECASE)


@pytest.mark.parametrize("path", TEMPLATE_FILES, ids=lambda p: p.name)
def test_d3_no_inline_event_handlers(path: Path) -> None:
    """[D-3] no ``on[a-z]+=`` attributes in templates."""
    text = path.read_text(encoding="utf-8")
    assert not re.search(r"\son[a-z]+\s*=", text, re.IGNORECASE)


@pytest.mark.parametrize("path", TEMPLATE_FILES, ids=lambda p: p.name)
def test_d3_no_external_links_in_templates(path: Path) -> None:
    """[D-3] no http(s):// (CDN) links in templates."""
    text = path.read_text(encoding="utf-8")
    assert not re.search(r"https?://", text)


def test_d3_no_external_urls_in_css_js() -> None:
    """[D-3] static CSS/JS reference no external hosts (no CDN / web fonts)."""
    for path in sorted(STATIC_DIR.rglob("*")):
        if path.suffix not in (".css", ".js"):
            continue
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"https?://", text), path


def test_d3_no_markup_bypass_in_python() -> None:
    """[D-3] web Python code does not bypass autoescape (Markup / autoescape=False)."""
    for path in sorted(WEB_SRC.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        assert "Markup(" not in text, path
        assert "autoescape=False" not in text, path
    assert templates.env.autoescape is True


def test_d3_strict_undefined_active() -> None:
    """[D-3] VINE_WEB_STRICT=1 → missing template variables raise."""
    with pytest.raises(UndefinedError):
        templates.env.from_string("{{ missing_var }}").render()


# --- D-4 static assets ---------------------------------------------------------------

_URL_FOR_RE = re.compile(r"url_for\('ui_static',\s*path=([^)]*)\)")
_LITERAL_RE = re.compile(r"'([^']+\.[a-z0-9]+)'")


def _template_asset_paths() -> set[str]:
    paths: set[str] = set()
    for template in TEMPLATE_FILES:
        for expr in _URL_FOR_RE.findall(template.read_text(encoding="utf-8")):
            paths.update(_LITERAL_RE.findall(expr))
    return paths


def test_d4_template_static_refs_exist(client: TestClient) -> None:
    """[D-4] every url_for('ui_static', path='…') literal → file served 200."""
    paths = _template_asset_paths()
    assert "css/app.css" in paths and "js/store.js" in paths
    for rel in sorted(paths):
        assert (STATIC_DIR / rel).is_file(), rel
        response = client.get(f"/ui-static/{rel}")
        assert response.status_code == 200, rel


def test_d4_rendered_pages_static_refs_200(client: TestClient) -> None:
    """[D-4] all /ui-static/… URLs in rendered pages (every state) → 200."""
    found = do_search(client, "found.jpg")
    low = do_search(client, "x_low.jpg")
    nf = do_search(client, "x_notfound.jpg")
    slug = "abrau-dyurso-abrau-estates-krasnoe-kaberne-sovinon-suhoe-13"
    paths = [
        "/",
        "/catalog",
        "/catalog?color=Оранжевое",
        "/me",
        f"/wine/{slug}",
        "/wine/unknown",
        f"/result/{found}",
        f"/result/{found}?analogs=1",
        f"/result/{found}?fb=1&verdict=match",
        f"/result/{low}",
        f"/result/{nf}",
    ]
    assets: set[str] = set()
    for path in paths:
        response = client.get(path)
        assert response.status_code in (200, 404), path
        assets.update(
            u for u in Page(response.text).asset_urls() if u.startswith("/ui-static/")
        )
    assert len(assets) >= 8
    for url in sorted(assets):
        assert client.get(url).status_code == 200, url


def test_d4_js_relative_imports_exist() -> None:
    """[D-4] ES-module relative imports in static/js resolve to files."""
    js_dir = STATIC_DIR / "js"
    for path in sorted(js_dir.glob("*.js")):
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"""from\s+["'](\.[^"']+)["']""", text):
            assert (path.parent / target).resolve().is_file(), (path.name, target)


def test_d4_css_url_refs_exist() -> None:
    """[D-4] url(...) references inside CSS point to existing files."""
    for path in sorted((STATIC_DIR / "css").glob("*.css")):
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", text):
            if target.startswith(("data:", "#")):
                continue
            if target.startswith("/ui-static/"):
                resolved = STATIC_DIR / target.removeprefix("/ui-static/")
            else:
                resolved = (path.parent / target).resolve()
            assert resolved.is_file(), (path.name, target)


# --- D-5 errors ----------------------------------------------------------------


class _Exploding(StubProductService):
    def get_wine(self, slug: str) -> WineCard | None:
        msg = "db password=secret123 exploded"
        raise RuntimeError(msg)


def test_d5_unhandled_error_renders_500_page_without_trace(
    make_client: Callable[..., TestClient],
) -> None:
    """[D-5] service exception → error.html 500, no stack trace / exception text."""
    client = make_client(_Exploding())
    response = client.get("/wine/anything")
    page = assert_html_page(response, 500)
    assert "secret123" not in response.text
    assert "RuntimeError" not in response.text
    assert "Что-то пошло не так" in page.text
