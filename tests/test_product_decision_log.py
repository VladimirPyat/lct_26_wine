"""PROD-API D — общий пайплайн run_search: поля decision log (без моделей и БД)."""

from __future__ import annotations

import contextlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from api import eval_pipeline
from api.eval_pipeline import EmptyCatalogError, predict_slug, run_search
from core.config import load_ocr_rerank_settings
from core.policy.decision import PolicyDecision
from core.retrieve.retriever import RetrieveBundle

HITS = [
    {
        "wine_id": i,
        "slug": f"wine-{i}",
        "score": 0.9 - 0.05 * i,
        "title": f"Wine {i}",
        "manufacturer": "M",
        "category": "Красное",
        "image_path": f"/static/wines/wine-{i}.webp",
        "grape_variety": "Мерло",
    }
    for i in range(1, 6)
]


def _decision(hits: list[dict]) -> PolicyDecision:
    return PolicyDecision(
        slug=hits[0]["slug"],
        garbage=False,
        margin=hits[0]["score"] - hits[1]["score"],
        score_1=hits[0]["score"],
        score_2=hits[1]["score"],
        enable_rerank=True,
        rerank_triggered=False,
        winner_before_rerank=hits[0]["slug"],
        winner_after_rerank=None,
        ocr_lines=[],
        hits=hits,  # type: ignore[arg-type]
    )


@pytest.fixture
def fake_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    settings = load_ocr_rerank_settings()
    log_settings = settings.decision_log.model_copy(update={"path": "decisions.jsonl"})
    runtime = SimpleNamespace(
        repo_root=tmp_path,
        ocr_rerank=settings.model_copy(update={"decision_log": log_settings}),
        cropper=None,
        encoder=SimpleNamespace(embedding_dim=768),
        encoder_model="fake.onnx",
        reranker=None,
        session_factory=None,
        get_ocr=lambda: None,
        hits=list(HITS),
    )

    class FakeRetriever:
        def __init__(self, cropper, encoder, repository) -> None:
            pass

        def retrieve_bundle(self, path: str, *, top_k: int) -> RetrieveBundle:
            return RetrieveBundle(
                crop_path=path, used_fallback=False, hits=runtime.hits[:top_k]
            )

    monkeypatch.setattr(
        eval_pipeline, "session_scope", lambda _f: contextlib.nullcontext(None)
    )
    monkeypatch.setattr(eval_pipeline, "WineRepository", lambda _s: None)
    monkeypatch.setattr(eval_pipeline, "WineRetriever", FakeRetriever)
    monkeypatch.setattr(
        eval_pipeline, "decide", lambda hits, **_kw: _decision(list(hits))
    )
    return runtime


def _records(tmp_path: Path) -> list[dict]:
    path = tmp_path / "decisions.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_eval_log_has_scores_no_product_fields(fake_runtime, tmp_path: Path) -> None:
    """[TEST-ID] PA-D3 eval: в логе score_1/score_2, продуктовых полей нет."""
    image = tmp_path / "q.jpg"
    image.write_bytes(b"x")
    assert predict_slug(fake_runtime, image) == "wine-1"
    (rec,) = _records(tmp_path)
    assert rec["score_1"] == pytest.approx(0.85)
    assert rec["score_2"] == pytest.approx(0.80)
    assert rec["winner"] == "wine-1"
    for key in ("search_id", "status", "confidence_level", "endpoint"):
        assert key not in rec


def test_product_log_fields_merged(fake_runtime, tmp_path: Path) -> None:
    """[TEST-ID] PA-D3b product: log_fields (search_id, status, ...) попадают в лог."""
    image = tmp_path / "q.jpg"
    image.write_bytes(b"x")
    seen: list[PolicyDecision] = []

    def fields(decision: PolicyDecision) -> dict[str, object]:
        seen.append(decision)
        return {
            "search_id": "a" * 32,
            "status": "found",
            "confidence_level": "high",
            "endpoint": "product",
        }

    run = run_search(fake_runtime, image, log_fields=fields)
    assert seen == [run.decision]
    (rec,) = _records(tmp_path)
    assert rec["search_id"] == "a" * 32
    assert rec["status"] == "found"
    assert rec["confidence_level"] == "high"
    assert rec["endpoint"] == "product"
    assert rec["score_1"] == pytest.approx(run.decision.score_1)
    assert rec["score_2"] == pytest.approx(run.decision.score_2)
    assert "total" in run.latency_ms


def test_run_search_missing_file_and_empty_catalog(
    fake_runtime, tmp_path: Path
) -> None:
    """[TEST-ID] PA-D3c нет файла / пустой каталог → исключение, лог не пишется."""
    with pytest.raises(FileNotFoundError):
        run_search(fake_runtime, tmp_path / "missing.jpg")
    image = tmp_path / "q.jpg"
    image.write_bytes(b"x")
    fake_runtime.hits = []
    with pytest.raises(EmptyCatalogError):
        run_search(fake_runtime, image)
    assert not (tmp_path / "decisions.jsonl").exists()
