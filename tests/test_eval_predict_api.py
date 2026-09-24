"""Stage 2B — HTTP smoke for POST /v1/eval/predict."""

from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock

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


def test_eval_predict_empty_upload_400(predict_client: TestClient) -> None:
    """[TEST-ID] 2B-05b empty image upload → 400."""
    files = {"image": ("empty.jpg", BytesIO(b""), "image/jpeg")}
    response = predict_client.post("/v1/eval/predict", files=files)
    assert response.status_code == 400
