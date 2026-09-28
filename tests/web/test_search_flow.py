"""WEB-UI §B: search flow — upload, result states, feedback, photo."""

from __future__ import annotations

import re
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from web_helpers import (
    JPEG_BYTES,
    PNG_BYTES,
    UNKNOWN_ID,
    Page,
    SpyService,
    assert_html_page,
    do_search,
    upload,
)

from core.config import ProductSettings, UploadSettings
from core.product import StubProductService
from web.router import _TMP_UPLOADS

WINNER_TITLE = "Abrau Estates красное"
WINNER_URL = (
    "https://vino-svoe.ru/wines/"
    "abrau-dyurso-abrau-estates-krasnoe-kaberne-sovinon-suhoe-13"
)


def _result(client: TestClient, search_id: str, query: str = "") -> Page:
    return assert_html_page(client.get(f"/result/{search_id}{query}"), 200)


def _has_analogs_block(page: Page) -> bool:
    return page.has("section", id="analogs")


def _small_upload_settings(settings: ProductSettings, max_mb: float) -> ProductSettings:
    upload_settings = UploadSettings(
        max_mb=max_mb, content_types=list(settings.upload.content_types)
    )
    return settings.model_copy(update={"upload": upload_settings})


def _tmp_uploads() -> set[str]:
    if not _TMP_UPLOADS.is_dir():
        return set()
    return {p.name for p in _TMP_UPLOADS.iterdir()}


# --- B-1 found ---------------------------------------------------------------


def test_b1_search_redirects_303_to_result(client: TestClient) -> None:
    """[B-1] POST /search jpg → 303 Location /result/{32hex}."""
    before = _tmp_uploads()
    response = upload(client, "bottle.jpg")
    assert response.status_code == 303
    location = response.headers["location"]
    assert location.startswith("/result/")
    assert len(location.removeprefix("/result/")) == 32
    assert _tmp_uploads() == before, "temporary upload not cleaned up"


def test_b1_search_follow_redirect_lands_on_result(client: TestClient) -> None:
    """[B-1] following the redirect renders the result page."""
    response = client.post(
        "/search", files={"image": ("bottle.jpg", JPEG_BYTES, "image/jpeg")}
    )
    page = assert_html_page(response, 200)
    assert WINNER_TITLE in page.text
    assert str(response.url.path).startswith("/result/")


def test_b1_found_state(client: TestClient) -> None:
    """[B-1] found: title, level, site link, feedback, analogs button, no analogs."""
    search_id = do_search(client, "bottle.jpg")
    page = _result(client, search_id)

    assert WINNER_TITLE in page.text
    assert "Высокая уверенность" in page.text

    site = [a for a in page.find_all("a") if a.get("href") == WINNER_URL]
    assert site, "«Открыть на сайте» link missing"
    assert "Открыть на сайте" in page.text
    for link in site:
        assert link.get("target") == "_blank"
        assert set((link.get("rel") or "").split()) >= {"noopener", "noreferrer"}

    assert "Это то вино?" in page.text
    forms = page.find_all("form", action=f"/result/{search_id}/feedback")
    assert forms and (forms[0].get("method") or "").lower() == "post"
    assert page.has("button", name="verdict", value="match")
    assert page.has("button", name="verdict", value="mismatch")

    assert "Подобрать аналоги" in page.text
    assert any(
        href.startswith(f"/result/{search_id}?analogs=1") for href in page.links()
    )
    assert not _has_analogs_block(page)
    assert "Исходное фото" in page.text
    assert f"/result/{search_id}/photo" in page.links()


def test_b1_found_does_not_show_candidates(
    client: TestClient, stub: StubProductService
) -> None:
    """[B-1] candidates (top-K) are API-only: other wines absent on found page."""
    search_id = do_search(client, "bottle.jpg")
    result = stub.get_search(search_id)
    assert result is not None
    page = _result(client, search_id)
    for candidate in result.candidates[1:]:
        assert candidate.title not in page.text


# --- B-2 low / not_found -------------------------------------------------------


def test_b2_low_state(client: TestClient) -> None:
    """[B-2] *_low.jpg → low badge + analogs block shown immediately + feedback."""
    search_id = do_search(client, "bottle_low.jpg")
    page = _result(client, search_id)
    assert WINNER_TITLE in page.text
    assert "Низкая уверенность" in page.text
    assert "возможно, это не то вино" in page.text
    assert _has_analogs_block(page)
    assert "Похожие по этикетке" in page.text
    assert "Это то вино?" in page.text
    assert "Высокая уверенность" not in page.text


def test_b2_not_found_state(client: TestClient) -> None:
    """[B-2] *_notfound.jpg → message + analogs + /catalog?… link, no winner card."""
    search_id = do_search(client, "bottle_notfound.jpg")
    page = _result(client, search_id)
    assert "Вино не найдено в каталоге" in page.text
    assert "Воспользуйтесь подбором аналогов" in page.text
    assert _has_analogs_block(page)
    refine = [
        a for a in page.find_all("a") if (a.get("href") or "").startswith("/catalog?")
    ]
    assert refine, "link to /catalog?… with filters missing"
    assert "Уточнить в каталоге" in page.text
    assert not page.has(cls="badge"), "confidence badge must not be shown"
    assert not page.has(cls="wine__title"), "winner card must not be shown"
    assert not page.has(cls="result__info")
    assert "Высокая уверенность" not in page.text


def test_b2_not_found_refine_link_carries_ocr_filters(client: TestClient) -> None:
    """[B-2] «Уточнить в каталоге» carries the same filters as the analogs block."""
    search_id = do_search(client, "x_notfound.jpg")
    page = _result(client, search_id)
    refine = [
        a.get("href") or ""
        for a in page.find_all("a", cls="btn")
        if (a.get("href") or "").startswith("/catalog?")
    ]
    assert refine
    assert "color=" in refine[0]
    assert "grape=" in refine[0]


# --- B-3 ?analogs=1 -------------------------------------------------------------


def test_b3_found_with_analogs_param(client: TestClient) -> None:
    """[B-3] ?analogs=1 on found → «Аналоги от других виноделен» block, button gone."""
    search_id = do_search(client, "bottle.jpg")
    page = _result(client, search_id, "?analogs=1")
    assert _has_analogs_block(page)
    assert "Аналоги от других виноделен" in page.text
    assert "101 оттенок красного. Каберне" in page.text
    assert not any(
        href.startswith(f"/result/{search_id}?analogs=1") for href in page.links()
    )


def test_b3_analogs_param_ignored_values(client: TestClient) -> None:
    """[B-3] analogs block only for analogs=1."""
    search_id = do_search(client, "bottle.jpg")
    page = _result(client, search_id, "?analogs=0")
    assert not _has_analogs_block(page)


# --- B-4 upload validation --------------------------------------------------------


def test_b4_no_file_400(make_client: Callable[..., TestClient]) -> None:
    """[B-4] no file → 400 re-render of scanner with error; service not called."""
    spy = SpyService(StubProductService())
    client = make_client(spy)
    for response in (
        client.post("/search", data={"other": "1"}, follow_redirects=False),
        client.post(
            "/search",
            files={"other": ("a.txt", b"x", "text/plain")},
            follow_redirects=False,
        ),
    ):
        page = assert_html_page(response, 400)
        assert page.has("form", action="/search")
        errors = page.find_all(cls="form-error")
        assert errors and errors[0].get("hidden") is None
        assert "Выберите фото" in page.text
    assert "search" not in spy.calls


def test_b4_empty_file_400(client: TestClient) -> None:
    """[B-4] empty file → 400 with error."""
    page = assert_html_page(upload(client, "empty.jpg", b""), 400)
    assert page.has("form", action="/search")


def test_b4_oversized_413_with_small_limit(
    make_client: Callable[..., TestClient], product_settings: ProductSettings
) -> None:
    """[B-4] > upload.max_mb (from app.state.product_settings) → 413."""
    spy = SpyService(StubProductService())
    settings = _small_upload_settings(product_settings, max_mb=0.001)
    client = make_client(spy, settings)
    data = JPEG_BYTES + b"\x00" * 2048
    page = assert_html_page(upload(client, "big.jpg", data), 413)
    assert "слишком большой" in page.text
    assert "search" not in spy.calls


def test_b4_oversized_413_default_config(
    client: TestClient, product_settings: ProductSettings
) -> None:
    """[B-4] > config max_mb (15 MB) → 413."""
    max_bytes = int(product_settings.upload.max_mb * 1024 * 1024)
    data = JPEG_BYTES + b"\x00" * (max_bytes + 1 - len(JPEG_BYTES))
    assert_html_page(upload(client, "big.jpg", data), 413)


def test_b4_exact_limit_accepted(
    make_client: Callable[..., TestClient], product_settings: ProductSettings
) -> None:
    """[B-4] exactly max bytes is accepted."""
    settings = _small_upload_settings(product_settings, max_mb=0.001)
    client = make_client(StubProductService(), settings)
    max_bytes = int(0.001 * 1024 * 1024)
    data = JPEG_BYTES + b"\x00" * (max_bytes - len(JPEG_BYTES))
    assert upload(client, "edge.jpg", data).status_code == 303


def test_b4_text_plain_415(make_client: Callable[..., TestClient]) -> None:
    """[B-4] text/plain → 415, service not called."""
    spy = SpyService(StubProductService())
    client = make_client(spy)
    page = assert_html_page(upload(client, "a.txt", b"hello world", "text/plain"), 415)
    assert "Неподдерживаемый формат" in page.text
    assert page.has("form", action="/search")
    assert "search" not in spy.calls


def test_b4_gif_415(client: TestClient) -> None:
    """[B-4] GIF (not in content_types) → 415."""
    assert_html_page(
        upload(client, "a.gif", b"GIF89a" + b"\x00" * 32, "image/gif"), 415
    )


def test_b4_broken_declared_jpeg_400(client: TestClient) -> None:
    """[B-4] declared image/jpeg but not an image → 400 (documented deviation)."""
    assert_html_page(upload(client, "fake.jpg", b"not an image at all"), 400)


def test_b4_png_accepted(client: TestClient) -> None:
    """[B-4] PNG in content_types → 303."""
    assert upload(client, "p.png", PNG_BYTES, "image/png").status_code == 303


def test_b4_rejects_leave_no_temp_files(client: TestClient) -> None:
    """[B-4] rejected uploads do not leave temp files."""
    before = _tmp_uploads()
    upload(client, "a.txt", b"hello", "text/plain")
    upload(client, "fake.jpg", b"garbage")
    assert _tmp_uploads() == before


# --- B-5 feedback -------------------------------------------------------------------


def test_b5_feedback_match(client: TestClient, stub: StubProductService) -> None:
    """[B-5] match → 303 to result ?fb=1; stub recorded; thank-you shown."""
    search_id = do_search(client, "bottle.jpg")
    winner = stub.get_search(search_id)
    assert winner is not None and winner.winner is not None
    response = client.post(
        f"/result/{search_id}/feedback",
        data={"verdict": "match", "slug": winner.winner.slug},
        follow_redirects=False,
    )
    assert response.status_code == 303
    location = response.headers["location"]
    assert location.startswith(f"/result/{search_id}?")
    assert "fb=1" in location

    recorded = stub.feedback
    assert len(recorded) == 1
    assert recorded[0].search_id == search_id
    assert recorded[0].verdict == "match"
    assert recorded[0].slug == winner.winner.slug

    page = assert_html_page(client.get(location.split("#")[0]), 200)
    assert "Спасибо" in page.text
    assert not page.find_all("form", action=f"/result/{search_id}/feedback")


def test_b5_feedback_without_slug_uses_winner(
    client: TestClient, stub: StubProductService
) -> None:
    """[B-5] slug optional: server fills winner slug."""
    search_id = do_search(client, "bottle.jpg")
    response = client.post(
        f"/result/{search_id}/feedback",
        data={"verdict": "match"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    result = stub.get_search(search_id)
    assert result is not None and result.winner is not None
    assert stub.feedback[-1].slug == result.winner.slug


def test_b5_feedback_mismatch_shows_analogs_button(
    client: TestClient, stub: StubProductService
) -> None:
    """[B-5] mismatch → thank-you state + «Подобрать аналоги»."""
    search_id = do_search(client, "bottle.jpg")
    response = client.post(
        f"/result/{search_id}/feedback",
        data={"verdict": "mismatch"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert stub.feedback[-1].verdict == "mismatch"
    page = assert_html_page(client.get(response.headers["location"].split("#")[0]), 200)
    assert "Спасибо" in page.text
    thanks_links = [
        a
        for a in page.find_all("a", cls="btn--primary")
        if (a.get("href") or "").startswith(f"/result/{search_id}?analogs=1")
    ]
    assert thanks_links, "«Подобрать аналоги» missing after mismatch"


@pytest.mark.parametrize("verdict", ["", "maybe", "MATCH"])
def test_b5_feedback_invalid_verdict_400(
    client: TestClient, stub: StubProductService, verdict: str
) -> None:
    """[B-5] invalid verdict → 400 page, nothing recorded."""
    search_id = do_search(client, "bottle.jpg")
    response = client.post(
        f"/result/{search_id}/feedback",
        data={"verdict": verdict},
        follow_redirects=False,
    )
    assert_html_page(response, 400)
    assert stub.feedback == []


def test_b5_feedback_unknown_search_404(
    client: TestClient, stub: StubProductService
) -> None:
    """[B-5] feedback for unknown id → 404 page."""
    response = client.post(
        f"/result/{UNKNOWN_ID}/feedback",
        data={"verdict": "match"},
        follow_redirects=False,
    )
    assert_html_page(response, 404)
    assert stub.feedback == []


# --- B-6 photo -----------------------------------------------------------------------


def test_b6_photo(client: TestClient) -> None:
    """[B-6] /result/{id}/photo → 200 image, Cache-Control private."""
    search_id = do_search(client, "bottle.jpg")
    response = client.get(f"/result/{search_id}/photo")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/")
    assert "private" in response.headers.get("cache-control", "")
    assert response.content == JPEG_BYTES


def test_b6_photo_unknown_404(client: TestClient) -> None:
    """[B-6] unknown id → 404."""
    assert_html_page(client.get(f"/result/{UNKNOWN_ID}/photo"), 404)


# --- B-7 no raw scores ---------------------------------------------------------


def _decimal_patterns(value: float) -> list[re.Pattern[str]]:
    texts = {f"{value}", f"{value:.2f}"}
    texts |= {t.replace(".", ",") for t in texts}
    return [re.compile(rf"(?<![\w%]){re.escape(t)}(?!\d)") for t in texts]


def _percent_pattern(value: float) -> re.Pattern[str]:
    return re.compile(rf"(?<![\w.,]){round(value * 100)}\s?%")


@pytest.mark.parametrize(
    ("name", "query"),
    [
        ("bottle.jpg", ""),
        ("bottle.jpg", "?analogs=1"),
        ("bottle_low.jpg", ""),
        ("bottle_notfound.jpg", ""),
    ],
)
def test_b7_no_raw_scores_in_html(
    client: TestClient, stub: StubProductService, name: str, query: str
) -> None:
    """[B-7] confidence only as text level: no score_1 / margin / candidate scores."""
    search_id = do_search(client, name)
    result = stub.get_search(search_id)
    assert result is not None
    response = client.get(f"/result/{search_id}{query}")
    assert response.status_code == 200
    page = Page(response.text)
    values = [result.score_1, result.margin] + [c.score for c in result.candidates]
    for value in values:
        for pattern in _decimal_patterns(value):
            assert not pattern.search(response.text), f"raw score {value} leaked"
        percent = _percent_pattern(value)
        assert not percent.search(page.text), f"score {value} shown as percent"
    assert "score" not in response.text.lower()
    assert "cosine" not in response.text.lower()
