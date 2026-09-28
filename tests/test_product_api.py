"""PROD-API C — JSON API ``/api/v1`` через TestClient.

Два режима:
- валидация загрузки / 422 / 404 — ``StubProductService`` на ``app.state`` (без БД);
- полный поток — реальный ``CatalogProductService`` на Postgres, где только
  модельный пайплайн (``run_search``) заменён детерминированным (score задаётся тестом).
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from api.eval_pipeline import SearchRun
from api.routers.product import router as product_router
from core.policy.decision import PolicyDecision
from core.product import catalog_service as catalog_mod
from core.product.catalog_service import CatalogProductService
from core.product.schemas import AnalogsResult, CatalogFilters, SearchResult, WineCard
from core.product.stub import StubProductService
from product_helpers import build_db_service, make_settings

MB = 1024 * 1024


def _png_bytes(size: tuple[int, int] = (64, 96), color: str = "darkred") -> bytes:
    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def _jpeg_bytes() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (64, 96), "white").save(buf, format="JPEG")
    return buf.getvalue()


def _app(service: object, tmp_path: Path, max_mb: float = 1.0) -> FastAPI:
    app = FastAPI()
    app.include_router(product_router)
    app.state.eval_runtime = SimpleNamespace(repo_root=tmp_path)
    app.state.product_settings = make_settings(tmp_path, max_mb=max_mb)
    app.state.product_service = service
    return app


# --- validation (stub, no DB) --------------------------------------------


@pytest.fixture
def stub_client(tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(_app(StubProductService(), tmp_path)) as client:
        yield client


def test_upload_empty_400(stub_client: TestClient, tmp_path: Path) -> None:
    """[TEST-ID] PA-C3 пустой файл → 400, временный файл удалён."""
    r = stub_client.post(
        "/api/v1/search", files={"image": ("e.jpg", BytesIO(b""), "image/jpeg")}
    )
    assert r.status_code == 400
    assert set(r.json()) == {"detail"}
    assert list((tmp_path / "data" / "tmp" / "uploads").iterdir()) == []


def test_upload_undecodable_400(stub_client: TestClient, tmp_path: Path) -> None:
    """[TEST-ID] PA-C3b не-изображение с image/jpeg → 400."""
    r = stub_client.post(
        "/api/v1/search",
        files={"image": ("x.jpg", BytesIO(b"\xff\xd8\xffnot really"), "image/jpeg")},
    )
    assert r.status_code == 400
    assert "Traceback" not in r.text
    assert list((tmp_path / "data" / "tmp" / "uploads").iterdir()) == []


def test_upload_too_large_413(stub_client: TestClient, tmp_path: Path) -> None:
    """[TEST-ID] PA-C3c > max_mb (1 MB в тестовых настройках) → 413."""
    big = _png_bytes() + b"\0" * (MB + 10)
    r = stub_client.post(
        "/api/v1/search", files={"image": ("big.png", BytesIO(big), "image/png")}
    )
    assert r.status_code == 413
    assert list((tmp_path / "data" / "tmp" / "uploads").iterdir()) == []


def test_upload_exactly_max_ok(stub_client: TestClient) -> None:
    """[TEST-ID] PA-C3d ровно max_mb байт не отклоняется по размеру."""
    png = _png_bytes()
    exact = png + b"\0" * (MB - len(png))
    r = stub_client.post(
        "/api/v1/search", files={"image": ("ok.png", BytesIO(exact), "image/png")}
    )
    assert r.status_code == 200


@pytest.mark.parametrize(
    "ctype", ["text/plain", "application/octet-stream", "image/gif", "application/pdf"]
)
def test_upload_wrong_type_415(stub_client: TestClient, ctype: str) -> None:
    """[TEST-ID] PA-C3e text/plain и прочие типы → 415."""
    r = stub_client.post(
        "/api/v1/search", files={"image": ("a.txt", BytesIO(_png_bytes()), ctype)}
    )
    assert r.status_code == 415


def test_upload_missing_field_422(stub_client: TestClient) -> None:
    """[TEST-ID] PA-C3f нет поля image → 422."""
    r = stub_client.post(
        "/api/v1/search", files={"file": ("a.png", BytesIO(_png_bytes()), "image/png")}
    )
    assert r.status_code == 422


@pytest.mark.parametrize(
    "query", ["limit=0", "limit=51", "limit=-1", "offset=-1", "limit=abc"]
)
def test_wines_bad_paging_422(stub_client: TestClient, query: str) -> None:
    """[TEST-ID] PA-C4 /api/v1/wines?limit=0 (и др. вне 1..50) → 422."""
    assert stub_client.get(f"/api/v1/wines?{query}").status_code == 422


def test_wines_unknown_slug_404(stub_client: TestClient) -> None:
    """[TEST-ID] PA-C4b /api/v1/wines/{unknown} → 404 {"detail"}."""
    r = stub_client.get("/api/v1/wines/no-such-wine")
    assert r.status_code == 404
    assert set(r.json()) == {"detail"}


def test_search_unknown_404(stub_client: TestClient) -> None:
    """[TEST-ID] PA-C2b GET /search/{unknown} и /analogs → 404."""
    for sid in (uuid.uuid4().hex, "not-an-id"):
        assert stub_client.get(f"/api/v1/search/{sid}").status_code == 404
        assert stub_client.get(f"/api/v1/search/{sid}/analogs").status_code == 404


def test_analogs_limit_422(stub_client: TestClient) -> None:
    """[TEST-ID] PA-C4c /analogs?limit=0 → 422."""
    sid = uuid.uuid4().hex
    assert stub_client.get(f"/api/v1/search/{sid}/analogs?limit=0").status_code == 422


@pytest.mark.parametrize(
    "body",
    [
        {"search_id": "x", "verdict": "maybe"},
        {"verdict": "match"},
        {"search_id": "x"},
    ],
)
def test_feedback_invalid_body_422(stub_client: TestClient, body: dict) -> None:
    """[TEST-ID] PA-C5c невалидный FeedbackIn → 422."""
    assert stub_client.post("/api/v1/feedback", json=body).status_code == 422


def test_service_missing_503(tmp_path: Path) -> None:
    """[TEST-ID] PA-C6 сервис не инициализирован → 503."""
    app = FastAPI()
    app.include_router(product_router)
    with TestClient(app) as client:
        assert client.get("/api/v1/dictionaries").status_code == 503


# --- full flow on real DB service ----------------------------------------


@pytest.fixture(scope="module")
def db_service(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[CatalogProductService]:
    svc = build_db_service(tmp_path_factory.mktemp("product_api"))
    yield svc
    svc._runtime.engine.dispose()  # type: ignore[attr-defined]


class FakePipeline:
    """Подмена run_search: реальные вина из БД, score_1 задаётся тестом."""

    def __init__(self, service: CatalogProductService) -> None:
        wines, _ = service.find_wines(CatalogFilters(color="Красное"), limit=5)
        self.wines: list[WineCard] = wines
        self.score_1 = 0.9
        self.ocr_lines: list[str] = []
        self.winner_index = 0  # >0 simulates an OCR rerank switch
        self.calls: list[dict[str, object]] = []

    def __call__(self, runtime, image_path, *, log_fields=None) -> SearchRun:
        hits = [
            {
                "wine_id": i,
                "slug": w.slug,
                "score": self.score_1 - (i - 1) * 0.02,
                "title": w.title,
                "manufacturer": w.manufacturer,
                "category": w.color,
                "image_path": w.image_url,
                "grape_variety": w.grape_variety,
            }
            for i, w in enumerate(self.wines, start=1)
        ]
        winner = hits[self.winner_index]["slug"]
        decision = PolicyDecision(
            slug=winner,
            garbage=False,
            margin=0.02,
            score_1=hits[0]["score"],
            score_2=hits[1]["score"],
            enable_rerank=True,
            rerank_triggered=True,
            winner_before_rerank=hits[0]["slug"],
            winner_after_rerank=winner,
            ocr_lines=list(self.ocr_lines),
            hits=hits,  # type: ignore[arg-type]
        )
        fields = dict(log_fields(decision)) if log_fields is not None else {}
        self.calls.append({"image_path": Path(image_path), "log_fields": fields})
        bundle = SimpleNamespace(crop_path=str(image_path), hits=hits)
        return SearchRun(bundle=bundle, decision=decision, latency_ms={})  # type: ignore[arg-type]


@pytest.fixture
def flow(
    db_service: CatalogProductService, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[tuple[TestClient, FakePipeline, CatalogProductService]]:
    pipeline = FakePipeline(db_service)
    monkeypatch.setattr(catalog_mod, "run_search", pipeline)
    # Fresh storage + feedback log per test, thresholds from test settings.
    settings = make_settings(tmp_path, high_min=0.8, medium_min=0.65, not_found_min=0.5)
    monkeypatch.setattr(db_service, "_settings", settings)
    monkeypatch.setattr(db_service, "_queries_dir", Path(settings.storage.queries_dir))
    monkeypatch.setattr(db_service, "_feedback_log", Path(settings.feedback_log))
    Path(settings.storage.queries_dir).mkdir(parents=True)
    with TestClient(_app(db_service, tmp_path)) as client:
        yield client, pipeline, db_service


def _post_png(client: TestClient, name: str = "bottle.png"):
    return client.post(
        "/api/v1/search", files={"image": (name, BytesIO(_png_bytes()), "image/png")}
    )


@pytest.mark.db
@pytest.mark.parametrize(
    ("score", "status", "level"),
    [
        (0.9, "found", "high"),
        (0.8, "found", "high"),
        (0.7, "found", "medium"),
        (0.6, "low", "low"),
        (0.4, "not_found", "low"),
    ],
)
def test_search_flow_status_and_persist(
    flow, tmp_path: Path, score: float, status: str, level: str
) -> None:
    """[TEST-ID] PA-C1 POST /search → 200, валидный SearchResult.

    candidates ≤5 по убыванию, статус по порогам, GET = тело POST.
    """
    client, pipeline, service = flow
    pipeline.score_1 = score
    r = _post_png(client)
    assert r.status_code == 200, r.text
    body = r.json()
    result = SearchResult.model_validate(body)

    assert result.status == status
    assert result.confidence_level == level
    assert result.score_1 == pytest.approx(score)
    assert result.margin == pytest.approx(0.02)
    assert len(result.search_id) == 32 and int(result.search_id, 16) >= 0
    assert 0 < len(result.candidates) <= 5
    assert [c.rank for c in result.candidates] == list(
        range(1, len(result.candidates) + 1)
    )
    scores = [c.score for c in result.candidates]
    assert scores == sorted(scores, reverse=True)
    if status == "not_found":
        assert result.winner is None
    else:
        assert result.winner is not None
        assert result.winner.slug == result.candidates[0].slug
    if status == "found":
        assert result.analogs is None
    else:
        assert isinstance(result.analogs, AnalogsResult)

    # log fields computed from the same thresholds
    fields = pipeline.calls[-1]["log_fields"]
    assert fields["search_id"] == result.search_id
    assert fields["status"] == status
    assert fields["confidence_level"] == level
    assert fields["endpoint"] == "product"

    # photo + JSON persisted under exact id; upload temp file removed
    qdir = Path(service._queries_dir)
    assert (qdir / f"{result.search_id}.json").is_file()
    assert (
        service.query_photo_path(result.search_id) == qdir / f"{result.search_id}.png"
    )
    assert list((tmp_path / "data" / "tmp" / "uploads").iterdir()) == []

    # GET equals POST body
    g = client.get(f"/api/v1/search/{result.search_id}")
    assert g.status_code == 200
    assert g.json() == body


@pytest.mark.db
def test_search_low_uses_ocr_hint_analogs(flow) -> None:
    """[TEST-ID] PA-C1b low + OCR «КРАСНОЕ» → ocr_filters, победитель исключён."""
    client, pipeline, _service = flow
    pipeline.score_1 = 0.6
    pipeline.ocr_lines = ["ВИНО СТОЛОВОЕ", "КРАСНОЕ СУХОЕ"]
    result = SearchResult.model_validate(_post_png(client).json())
    assert result.status == "low"
    assert result.analogs is not None
    assert result.analogs.source == "ocr_filters"
    assert result.analogs.hints.color == "Красное"
    assert result.analogs.hints.ocr_ran is True
    assert result.analogs.filters.exclude_slugs == [result.winner.slug]
    assert result.winner.slug not in {w.slug for w in result.analogs.wines}
    assert all(w.color == "Красное" for w in result.analogs.wines)
    assert result.analogs.total > len(result.analogs.wines)


@pytest.mark.db
def test_search_low_rerank_switch_vector_excludes_winner(flow) -> None:
    """[TEST-ID] PA-C1d low + rerank выбрал rank 2, OCR без подсказок → vector.

    Аналоги не должны содержать сам победитель (как в ocr_filters / winner_filters).
    """
    client, pipeline, _service = flow
    pipeline.score_1 = 0.6
    pipeline.ocr_lines = ["2019"]
    pipeline.winner_index = 1
    result = SearchResult.model_validate(_post_png(client).json())
    assert result.status == "low"
    assert result.winner.slug == result.candidates[1].slug
    assert result.analogs is not None
    assert result.analogs.source == "vector"
    assert result.winner.slug not in {w.slug for w in result.analogs.wines}


@pytest.mark.db
def test_search_jpeg_extension(flow) -> None:
    """[TEST-ID] PA-C1c JPEG сохраняется как {id}.jpg по реальному формату."""
    client, _pipeline, service = flow
    r = client.post(
        "/api/v1/search",
        files={"image": ("photo.webp", BytesIO(_jpeg_bytes()), "image/jpeg")},
    )
    assert r.status_code == 200
    sid = r.json()["search_id"]
    assert service.query_photo_path(sid).name == f"{sid}.jpg"


@pytest.mark.db
def test_search_unsupported_real_format_400(flow) -> None:
    """[TEST-ID] PA-C3g GIF под видом image/png → 400, ничего не сохранено."""
    client, pipeline, service = flow
    buf = BytesIO()
    Image.new("RGB", (32, 32), "red").save(buf, format="GIF")
    r = client.post(
        "/api/v1/search",
        files={"image": ("a.png", BytesIO(buf.getvalue()), "image/png")},
    )
    assert r.status_code == 400
    assert pipeline.calls == []
    assert list(Path(service._queries_dir).iterdir()) == []


@pytest.mark.db
def test_found_analogs_endpoint(flow) -> None:
    """[TEST-ID] PA-C2c found → GET /analogs: winner_filters без его производителя."""
    client, pipeline, _service = flow
    pipeline.score_1 = 0.95
    result = SearchResult.model_validate(_post_png(client).json())
    r = client.get(f"/api/v1/search/{result.search_id}/analogs?limit=3")
    assert r.status_code == 200
    analogs = AnalogsResult.model_validate(r.json())
    assert analogs.source in {"winner_filters", "vector"}
    assert len(analogs.wines) <= 3
    assert result.winner.slug not in {w.slug for w in analogs.wines}
    if analogs.source == "winner_filters":
        assert all(w.manufacturer != result.winner.manufacturer for w in analogs.wines)


@pytest.mark.db
def test_feedback_204_and_jsonl(flow, tmp_path: Path) -> None:
    """[TEST-ID] PA-C5 POST /feedback → 204 и строка в JSONL; неизвестный id → 404."""
    client, pipeline, _service = flow
    pipeline.score_1 = 0.9
    result = SearchResult.model_validate(_post_png(client).json())
    r = client.post(
        "/api/v1/feedback", json={"search_id": result.search_id, "verdict": "match"}
    )
    assert r.status_code == 204
    assert r.content == b""
    lines = (
        (tmp_path / "search_feedback.jsonl").read_text(encoding="utf-8").splitlines()
    )
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["search_id"] == result.search_id
    assert rec["verdict"] == "match"
    assert rec["slug"] == rec["winner_slug"] == result.winner.slug
    assert rec["status"] == "found"

    r404 = client.post(
        "/api/v1/feedback", json={"search_id": uuid.uuid4().hex, "verdict": "match"}
    )
    assert r404.status_code == 404
    assert len((tmp_path / "search_feedback.jsonl").read_text().splitlines()) == 1


@pytest.mark.db
def test_wines_and_dictionaries_endpoints(flow) -> None:
    """[TEST-ID] PA-C4d /wines (items+total), /wines/{slug}, /dictionaries."""
    client, _pipeline, service = flow
    r = client.get("/api/v1/wines", params={"color": "Красное", "limit": 5})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"items", "total"}
    assert len(body["items"]) == 5 and body["total"] > 5
    ratings = [
        w["public_rating"] for w in body["items"] if w["public_rating"] is not None
    ]
    assert ratings == sorted(ratings, reverse=True)
    slug = body["items"][0]["slug"]
    w = client.get(f"/api/v1/wines/{slug}")
    assert w.status_code == 200
    assert WineCard.model_validate(w.json()).slug == slug
    d = client.get("/api/v1/dictionaries")
    assert d.status_code == 200
    assert d.json() == service.dictionaries().model_dump()
    # empty query params are ignored, not treated as filters
    e = client.get("/api/v1/wines", params={"color": "", "limit": 1})
    assert e.status_code == 200
    assert e.json()["total"] > body["total"]
