"""Stage 2B — HTTP smoke for POST /v1/eval/predict."""

from __future__ import annotations

import asyncio
import time
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers import eval as eval_router_mod
from api.routers.eval import router as eval_router


@pytest.fixture
def predict_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Minimal app with eval router; runtime stubbed on app.state."""
    app = FastAPI()
    app.include_router(eval_router)
    runtime = SimpleNamespace(repo_root=MagicMock())
    # Path ops used by handler: mkdir + NamedTemporaryFile dir
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    runtime.repo_root = root
    app.state.eval_runtime = runtime

    monkeypatch.setattr(
        eval_router_mod,
        "predict_slug",
        lambda _runtime, _path: "agora-muskat-chernyj",
    )
    return TestClient(app)


def test_eval_predict_multipart_returns_slug(predict_client: TestClient) -> None:
    """[TEST-ID] 2B-05 multipart image → {\"slug\": \"...\"} status 200."""
    files = {
        "image": ("query.jpg", BytesIO(b"\xff\xd8\xfffakejpeg"), "image/jpeg"),
    }
    response = predict_client.post("/v1/eval/predict", files=files)

    assert response.status_code == 200
    body = response.json()
    assert body == {"slug": "agora-muskat-chernyj"}
    assert isinstance(body["slug"], str) and body["slug"]


def test_eval_predict_does_not_block_other_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Slow inference runs off the event loop: a parallel request is not stalled."""
    predict_seconds = 0.8
    app = FastAPI()
    app.include_router(eval_router)
    repo_root = Path(__file__).resolve().parents[1]
    app.state.eval_runtime = SimpleNamespace(repo_root=repo_root)

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"status": "ok"}

    def slow_predict(_runtime: object, _path: object) -> str:
        time.sleep(predict_seconds)
        return "agora-muskat-chernyj"

    monkeypatch.setattr(eval_router_mod, "predict_slug", slow_predict)

    async def scenario() -> tuple[float, float, int]:
        transport = httpx.ASGITransport(app=app)
        client = httpx.AsyncClient(transport=transport, base_url="http://t")
        async with client:
            files = {"image": ("q.jpg", b"\xff\xd8\xfffakejpeg", "image/jpeg")}
            started = time.perf_counter()
            predict = asyncio.create_task(client.post("/v1/eval/predict", files=files))
            await asyncio.sleep(0.1)
            await client.get("/ping")
            ping_done = time.perf_counter() - started
            status = (await predict).status_code
            predict_done = time.perf_counter() - started
            return ping_done, predict_done, status

    ping_done, predict_done, predict_status = asyncio.run(scenario())
    assert predict_status == 200
    assert predict_done >= predict_seconds
    assert ping_done < predict_seconds / 2


def test_eval_predict_empty_upload_400(predict_client: TestClient) -> None:
    """[TEST-ID] 2B-05b empty image upload → 400."""
    files = {"image": ("empty.jpg", BytesIO(b""), "image/jpeg")}
    response = predict_client.post("/v1/eval/predict", files=files)
    assert response.status_code == 400


# --- PROD-API-FIX1: effective OCR engine "none" -----------------------------


def _near_tie_hits() -> list[dict[str, object]]:
    return [
        {
            "wine_id": i,
            "slug": slug,
            "score": score,
            "title": slug,
            "manufacturer": "Maker",
            "category": "Красное",
            "image_path": f"/static/wines/{slug}.webp",
            "grape_variety": "Мерло",
        }
        for i, (slug, score) in enumerate(
            [("image-top-1", 0.61), ("close-second", 0.60), ("third", 0.50)], start=1
        )
    ]


@pytest.mark.parametrize("ocr_mode", ["none", "failed"])
def test_eval_predict_without_ocr_returns_top1(
    monkeypatch: pytest.MonkeyPatch, tmp_path, ocr_mode: str
) -> None:
    """[TEST-ID] FIX1-E1 effective none / сбой LLM OCR: near-tie → 200 {"slug": top-1}.

    Реальные ``predict_slug`` / ``run_search`` / ``decide``; подменены только
    retrieve (кандидаты) и OCR. Лог решения содержит score_1/score_2/rerank_reason.
    """
    import json
    from pathlib import Path

    from api import eval_pipeline
    from core.config import load_ocr_rerank_settings
    from core.ocr.base import OCRUnavailableError
    from core.retrieve.retriever import RetrieveBundle

    settings = load_ocr_rerank_settings()
    settings = settings.model_copy(
        update={
            "policy": settings.policy.model_copy(
                update={"enable_rerank": True, "margin_min": 0.1, "margin_tiers": []}
            )
        }
    )
    hits = _near_tie_hits()

    class _Retriever:
        def __init__(self, *_args: object) -> None:
            pass

        def retrieve_bundle(self, path: str, *, top_k: int) -> RetrieveBundle:
            return RetrieveBundle(
                crop_path=path, used_fallback=False, hits=hits  # type: ignore[arg-type]
            )

    class _FailingOcr:
        def recognize(self, _path: str) -> list[str]:
            raise OCRUnavailableError("LLM OCR failed (task=ocr_label)")

    monkeypatch.setattr(eval_pipeline, "WineRetriever", _Retriever)
    get_ocr_calls: list[int] = []

    def get_ocr():  # noqa: ANN202
        get_ocr_calls.append(1)
        return None if ocr_mode == "none" else _FailingOcr()

    reranker = MagicMock()
    runtime = SimpleNamespace(
        repo_root=Path(tmp_path),
        ocr_rerank=settings,
        cropper=object(),
        encoder=SimpleNamespace(embedding_dim=8),
        reranker=reranker,
        session_factory=MagicMock(),
        encoder_model="test.onnx",
        get_ocr=get_ocr,
    )
    app = FastAPI()
    app.include_router(eval_router)
    app.state.eval_runtime = runtime
    client = TestClient(app)

    files = {"image": ("q.jpg", BytesIO(b"\xff\xd8\xfffakejpeg"), "image/jpeg")}
    response = client.post("/v1/eval/predict", files=files)
    assert response.status_code == 200, response.text
    assert response.json() == {"slug": "image-top-1"}
    assert get_ocr_calls == [1]
    reranker.rerank.assert_not_called()

    log_path = Path(settings.decision_log.path)
    if not log_path.is_absolute():
        log_path = Path(tmp_path) / log_path
    records = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert len(records) == 1
    rec = records[0]
    assert rec["score_1"] == pytest.approx(0.61)
    assert rec["score_2"] == pytest.approx(0.60)
    assert rec["rerank_reason"] == (
        "ocr_unavailable" if ocr_mode == "none" else "ocr_failed"
    )
    assert rec["rerank_triggered"] is False
