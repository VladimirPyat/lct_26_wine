"""PROD-API C (live) — ``/api/v1`` на реальном рантайме (uvicorn, модели + БД).

Сервер: ``PRODUCT_API_BASE`` (по умолчанию ``http://127.0.0.1:8081``);
недоступен → skip.
Feedback здесь не отправляется, чтобы не писать тестовые строки в рабочий JSONL
(покрыто в ``test_product_api.py`` на tmp_path).
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path

import httpx
import pytest

from core.config import load_product_settings
from core.product.catalog_service import classify_confidence
from core.product.schemas import AnalogsResult, SearchResult

pytestmark = pytest.mark.e2e

REPO_ROOT = Path(__file__).resolve().parents[1]
SET1 = REPO_ROOT / "data" / "owner_eval" / "1"
BASE = os.environ.get("PRODUCT_API_BASE", "http://127.0.0.1:8081").rstrip("/")
TIMEOUT = httpx.Timeout(120.0, connect=3.0)


@pytest.fixture(scope="module")
def client() -> httpx.Client:
    try:
        httpx.get(f"{BASE}/health", timeout=3.0).raise_for_status()
    except httpx.HTTPError as err:
        pytest.skip(f"live API not reachable at {BASE}: {type(err).__name__}")
    with httpx.Client(base_url=BASE, timeout=TIMEOUT) as c:
        yield c


def _expected_slugs() -> dict[str, str]:
    mapping = json.loads((SET1 / "mapping.json").read_text(encoding="utf-8"))
    cases = mapping["cases"] if isinstance(mapping, dict) else mapping
    return {c["image_path"]: c["expected_slug"] for c in cases}


def _first_query_image() -> Path:
    with (SET1 / "queries.tsv").open(encoding="utf-8") as fh:
        row = next(csv.DictReader(fh, delimiter="\t"))
    return SET1 / "queries" / row["image_path"]


def test_live_search_owner_eval_image(client: httpx.Client) -> None:
    """[TEST-ID] PA-C1-live owner_eval фото → 200, валидный SearchResult.

    candidates ≤5 по убыванию, статус по порогам сервера, GET = тело POST.
    """
    image = _first_query_image()
    if not image.is_file():
        pytest.skip(f"owner_eval image missing: {image.name}")
    with image.open("rb") as fh:
        r = client.post(
            "/api/v1/search", files={"image": (image.name, fh, "image/jpeg")}
        )
    assert r.status_code == 200, r.text
    body = r.json()
    result = SearchResult.model_validate(body)

    assert 0 < len(result.candidates) <= 5
    scores = [c.score for c in result.candidates]
    assert scores == sorted(scores, reverse=True)
    assert result.score_1 == pytest.approx(result.candidates[0].score, abs=1e-6)
    thresholds = load_product_settings().confidence  # what the server loaded
    assert (result.status, result.confidence_level) == classify_confidence(
        result.score_1, thresholds
    )
    if result.status != "not_found":
        assert result.winner is not None
        expected = _expected_slugs().get(image.name)
        if expected is not None:
            assert result.winner.slug == expected
    if result.status == "found":
        assert result.analogs is None

    g = client.get(f"/api/v1/search/{result.search_id}")
    assert g.status_code == 200
    assert g.json() == body

    a = client.get(f"/api/v1/search/{result.search_id}/analogs", params={"limit": 5})
    assert a.status_code == 200
    analogs = AnalogsResult.model_validate(a.json())
    assert len(analogs.wines) <= 5
    if result.winner is not None:
        assert result.winner.slug not in {w.slug for w in analogs.wines}
        if analogs.source == "winner_filters":
            assert all(
                w.manufacturer != result.winner.manufacturer for w in analogs.wines
            )


def test_live_error_codes(client: httpx.Client) -> None:
    """[TEST-ID] PA-C3-live 400 / 415 / 404 / 422 на живом сервере."""
    empty = client.post("/api/v1/search", files={"image": ("e.jpg", b"", "image/jpeg")})
    assert empty.status_code == 400
    txt = client.post("/api/v1/search", files={"image": ("a.txt", b"hi", "text/plain")})
    assert txt.status_code == 415
    assert client.get("/api/v1/search/" + "0" * 32).status_code == 404
    assert client.get("/api/v1/wines", params={"limit": 0}).status_code == 422
    assert client.get("/api/v1/wines/no-such-wine-xyz").status_code == 404
    fb = client.post(
        "/api/v1/feedback", json={"search_id": "0" * 32, "verdict": "match"}
    )
    assert fb.status_code == 404
