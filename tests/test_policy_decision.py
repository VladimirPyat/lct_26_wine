"""Stage 2B — decision policy: margin, enable_rerank, abs_min garbage."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from core.config import PolicySettings
from core.contracts import RankedHit
from core.ocr.base import OCRUnavailableError
from core.policy.decision import decide


def _hit(
    wine_id: int,
    slug: str,
    score: float,
    *,
    title: str | None = None,
) -> RankedHit:
    return RankedHit(
        wine_id=wine_id,
        slug=slug,
        score=score,
        title=title or slug.replace("-", " "),
        manufacturer="Maker",
        category="wine",
        image_path=f"/static/wines/{slug}.webp",
    )


def _policy(**overrides: Any) -> PolicySettings:
    base = {
        "top_k": 5,
        "margin_min": 0.1,
        "abs_min": 0.2,
        "enable_rerank": True,
        "enable_not_found_gate": False,
    }
    base.update(overrides)
    return PolicySettings.model_validate(base)


def test_large_margin_skips_ocr() -> None:
    """[TEST-ID] 2B-01 large margin → no OCR; winner = top-1."""
    hits = [
        _hit(1, "winner-a", 0.95),
        _hit(2, "runner-b", 0.70),
    ]
    ocr = MagicMock()
    ocr.recognize.return_value = ["SHOULD_NOT_RUN"]
    ocr_factory = MagicMock(return_value=ocr)
    reranker = MagicMock()

    decision = decide(
        hits,
        crop_path="/tmp/crop.jpg",
        policy=_policy(margin_min=0.1, enable_rerank=True),
        ocr_factory=ocr_factory,
        reranker=reranker,
        rerank_top=5,
    )

    assert decision.slug == "winner-a"
    assert decision.rerank_triggered is False
    assert decision.garbage is False
    assert decision.margin == pytest.approx(0.25)
    ocr_factory.assert_not_called()
    ocr.recognize.assert_not_called()
    reranker.rerank.assert_not_called()


def test_small_margin_triggers_ocr_when_rerank_enabled() -> None:
    """[TEST-ID] 2B-02 small margin + enable_rerank → OCR called (mock)."""
    hits = [
        _hit(1, "top-visual", 0.55, title="Alpha Wine"),
        _hit(2, "ocr-winner", 0.50, title="Beta Wine"),
    ]
    ocr = MagicMock()
    ocr.recognize.return_value = ["Beta Wine"]
    ocr_factory = MagicMock(return_value=ocr)
    reranker = MagicMock()
    reranker.rerank.return_value = [{"wine_id": 2, "score": 9.0}]

    decision = decide(
        hits,
        crop_path="/tmp/crop.jpg",
        policy=_policy(margin_min=0.1, enable_rerank=True),
        ocr_factory=ocr_factory,
        reranker=reranker,
        rerank_top=5,
    )

    assert decision.rerank_triggered is True
    assert decision.margin == pytest.approx(0.05)
    assert decision.slug == "ocr-winner"
    assert decision.winner_before_rerank == "top-visual"
    assert decision.winner_after_rerank == "ocr-winner"
    assert decision.ocr_lines == ["Beta Wine"]
    ocr_factory.assert_called_once()
    ocr.recognize.assert_called_once_with("/tmp/crop.jpg")
    reranker.rerank.assert_called_once()


def test_enable_rerank_false_never_calls_ocr() -> None:
    """[TEST-ID] 2B-03 enable_rerank=false → never OCR even if margin tiny."""
    hits = [
        _hit(1, "keep-top", 0.41),
        _hit(2, "close-second", 0.40),
    ]
    ocr = MagicMock()
    ocr_factory = MagicMock(return_value=ocr)
    reranker = MagicMock()

    decision = decide(
        hits,
        crop_path="/tmp/crop.jpg",
        policy=_policy(margin_min=0.1, enable_rerank=False),
        ocr_factory=ocr_factory,
        reranker=reranker,
        rerank_top=5,
    )

    assert decision.slug == "keep-top"
    assert decision.enable_rerank is False
    assert decision.rerank_triggered is False
    assert decision.margin == pytest.approx(0.01)
    ocr_factory.assert_not_called()
    ocr.recognize.assert_not_called()
    reranker.rerank.assert_not_called()


def test_abs_min_garbage_still_returns_top1() -> None:
    """[TEST-ID] 2B-04 score_1 < abs_min → garbage; slug still top-1."""
    hits = [
        _hit(1, "weak-top", 0.05),
        _hit(2, "weak-second", 0.04),
    ]
    ocr_factory = MagicMock()
    reranker = MagicMock()

    decision = decide(
        hits,
        crop_path="/tmp/crop.jpg",
        policy=_policy(abs_min=0.2, enable_rerank=False),
        ocr_factory=ocr_factory,
        reranker=reranker,
        rerank_top=5,
    )

    assert decision.garbage is True
    assert decision.score_1 == pytest.approx(0.05)
    assert decision.slug == "weak-top"
    ocr_factory.assert_not_called()


# --- PROD-API-FIX1: OCR unavailable / failed ------------------------------


def _near_tie() -> list[RankedHit]:
    return [
        _hit(1, "image-top", 0.55, title="Alpha Wine"),
        _hit(2, "text-leader", 0.52, title="Beta Wine"),
    ]


def test_ocr_factory_none_skips_rerank() -> None:
    """[TEST-ID] FIX1-P1 ocr_factory → None на near-tie: top-1,
    rerank_reason=ocr_unavailable.
    """
    hits = _near_tie()
    reranker = MagicMock()
    decision = decide(
        hits,
        crop_path="/tmp/crop.jpg",
        policy=_policy(margin_min=0.1, enable_rerank=True),
        ocr_factory=lambda: None,
        reranker=reranker,
        rerank_top=5,
    )
    assert decision.slug == hits[0]["slug"]
    assert decision.rerank_triggered is False
    assert decision.rerank_reason == "ocr_unavailable"
    assert decision.winner_after_rerank is None
    assert decision.ocr_lines == []
    assert decision.enable_rerank is True
    reranker.rerank.assert_not_called()


def test_ocr_unavailable_error_skips_rerank() -> None:
    """[TEST-ID] FIX1-P2 recognize → OCRUnavailableError: top-1,
    rerank_reason=ocr_failed.
    """
    hits = _near_tie()
    ocr = MagicMock()
    ocr.recognize.side_effect = OCRUnavailableError("LLM OCR failed (task=ocr_label)")
    reranker = MagicMock()
    decision = decide(
        hits,
        crop_path="/tmp/crop.jpg",
        policy=_policy(margin_min=0.1, enable_rerank=True),
        ocr_factory=MagicMock(return_value=ocr),
        reranker=reranker,
        rerank_top=5,
    )
    assert decision.slug == hits[0]["slug"]
    assert decision.rerank_triggered is False
    assert decision.rerank_reason == "ocr_failed"
    assert decision.ocr_lines == []
    ocr.recognize.assert_called_once_with("/tmp/crop.jpg")
    reranker.rerank.assert_not_called()


@pytest.mark.parametrize("error", [RuntimeError("PHOCR CUDA OOM"), OSError("onnx")])
def test_other_ocr_errors_propagate(error: Exception) -> None:
    """[TEST-ID] FIX1-P3 иные ошибки OCR (PHOCR) не проглатываются."""
    ocr = MagicMock()
    ocr.recognize.side_effect = error
    with pytest.raises(type(error)):
        decide(
            _near_tie(),
            crop_path="/tmp/crop.jpg",
            policy=_policy(margin_min=0.1, enable_rerank=True),
            ocr_factory=MagicMock(return_value=ocr),
            reranker=MagicMock(),
            rerank_top=5,
        )


def test_ocr_factory_none_not_called_on_large_margin() -> None:
    """[TEST-ID] FIX1-P4 большой margin → фабрика OCR не вызывается, rerank_reason None.
    """
    factory = MagicMock(return_value=None)
    decision = decide(
        [_hit(1, "a", 0.9), _hit(2, "b", 0.5)],
        crop_path="/tmp/crop.jpg",
        policy=_policy(margin_min=0.1, enable_rerank=True),
        ocr_factory=factory,
        reranker=MagicMock(),
        rerank_top=5,
    )
    assert decision.slug == "a"
    assert decision.rerank_reason is None
    factory.assert_not_called()
