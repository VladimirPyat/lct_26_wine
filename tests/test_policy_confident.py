"""SIG-006 — confident OCR rerank policy + label_evidence on the real FuzzyReranker."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from core.config import OcrRerankSettings, load_ocr_rerank_settings
from core.contracts import RankedHit
from core.policy.decision import PolicyDecision, decide
from core.policy.logging import emit_decision_log
from core.text.fuzzy import FuzzyReranker

_AGORA = "AGORA WINERY"
_OCR_CAB = ["AGORA", "CABERNET", "SAUVIGNON", "YACHTING"]
# Synthetic top-2 gaps below (0.02–0.05) must trigger OCR regardless of the prod value.
_TEST_MARGIN_MIN = 0.08


@pytest.fixture(scope="module")
def settings() -> OcrRerankSettings:
    return load_ocr_rerank_settings()


@pytest.fixture(scope="module")
def reranker(settings: OcrRerankSettings) -> FuzzyReranker:
    return FuzzyReranker(
        settings.field_weights,
        settings.fuzzy,
        min_line_chars=settings.ocr.min_line_chars,
        drop_spaced_letters=settings.ocr.drop_spaced_letters,
    )


def _hit(
    wine_id: int,
    slug: str,
    score: float,
    title: str,
    grape: str,
    manufacturer: str = _AGORA,
) -> RankedHit:
    return RankedHit(
        wine_id=wine_id,
        slug=slug,
        score=score,
        title=title,
        manufacturer=manufacturer,
        category="Красное",
        image_path=f"/static/wines/{slug}.webp",
        grape_variety=grape,
    )


def _shiraz(score: float = 0.60) -> RankedHit:
    return _hit(1, "agora-yachting-shiraz", score, "Agora Yachting Shiraz", "Шираз")


def _cab(score: float = 0.58) -> RankedHit:
    return _hit(
        2,
        "agora-yachting-cabernet-sauvignon",
        score,
        "Agora Yachting Cabernet Sauvignon",
        "Каберне Совиньон",
    )


def _decide(
    hits: list[RankedHit],
    lines: list[str],
    settings: OcrRerankSettings,
    reranker: FuzzyReranker,
    **policy_overrides: Any,
) -> tuple[PolicyDecision, MagicMock]:
    policy = settings.policy.model_copy(
        update={
            "rerank_mode": "confident",
            "margin_min": _TEST_MARGIN_MIN,
            "margin_tiers": [],
            **policy_overrides,
        }
    )
    ocr = MagicMock()
    ocr.recognize.return_value = lines
    factory = MagicMock(return_value=ocr)
    decision = decide(
        hits,
        crop_path="/tmp/crop.jpg",
        policy=policy,
        ocr_factory=factory,
        reranker=reranker,
        rerank_top=settings.rerank_top,
    )
    return decision, factory


# --- decide(): rerank modes / reasons ---------------------------------------


def test_prod_policy_is_confident(settings: OcrRerankSettings) -> None:
    """[SIG-006] prod ocr_rerank.yaml: confident mode with manufacturer+grape combo."""
    assert settings.policy.rerank_mode == "confident"
    assert 0.0 < settings.policy.margin_min < 0.1
    assert ["manufacturer", "grape"] in settings.policy.strong_combos


def test_always_mode_text_leader_replaces_top1(
    settings: OcrRerankSettings, reranker: FuzzyReranker
) -> None:
    """[SIG-006] always: text leader wins (legacy behaviour)."""
    decision, _ = _decide(
        [_shiraz(), _cab()], _OCR_CAB, settings, reranker, rerank_mode="always"
    )
    assert decision.slug == "agora-yachting-cabernet-sauvignon"
    assert decision.rerank_reason == "always"
    assert decision.evidence == {}


def test_text_agrees_keeps_top1(
    settings: OcrRerankSettings, reranker: FuzzyReranker
) -> None:
    """[SIG-006] leader == image top-1 → text_agrees."""
    decision, _ = _decide(
        [_cab(0.60), _shiraz(0.58)], _OCR_CAB, settings, reranker
    )
    assert decision.slug == "agora-yachting-cabernet-sauvignon"
    assert decision.rerank_reason == "text_agrees"


def test_weak_text_only_manufacturer_keeps_top1(
    settings: OcrRerankSettings, reranker: FuzzyReranker
) -> None:
    """[SIG-006] OCR has only the shared producer → weak_text, keep top-1."""
    top = _hit(4, "agora-bastardo", 0.60, "Бастардо", "Бастардо")
    decision, _ = _decide([top, _shiraz(0.58)], ["AGORA"], settings, reranker)
    assert decision.text_leader == "agora-yachting-shiraz"
    assert decision.rerank_reason == "weak_text"
    assert decision.slug == "agora-bastardo"
    assert decision.evidence["agora-yachting-shiraz"] == {
        "manufacturer": True,
        "grapes": [],
        "brand": [],
    }


def test_strong_text_switches_to_confirmed_grape(
    settings: OcrRerankSettings, reranker: FuzzyReranker
) -> None:
    """[SIG-006] manufacturer + grape «Каберне Совиньон» confirmed → switch."""
    decision, _ = _decide([_shiraz(), _cab()], _OCR_CAB, settings, reranker)
    assert decision.slug == "agora-yachting-cabernet-sauvignon"
    assert decision.rerank_reason == "strong_text"
    assert decision.winner_before_rerank == "agora-yachting-shiraz"
    ev = decision.evidence["agora-yachting-cabernet-sauvignon"]
    assert ev["manufacturer"] is True
    assert ev["grapes"] == ["каберне совиньон"]


def test_not_distinguishing_grape_shared_with_top1(
    settings: OcrRerankSettings, reranker: FuzzyReranker
) -> None:
    """[SIG-006] confirmed grape also in top-1 grape_variety → keep."""
    top = _hit(
        5,
        "agora-yachting-red",
        0.60,
        "Agora Yachting Red",
        "Каберне Совиньон, Мерло",
    )
    decision, _ = _decide([top, _cab()], _OCR_CAB, settings, reranker)
    assert decision.text_leader == "agora-yachting-cabernet-sauvignon"
    assert decision.rerank_reason == "not_distinguishing"
    assert decision.slug == "agora-yachting-red"


def test_text_conflict_both_have_own_token(
    settings: OcrRerankSettings, reranker: FuzzyReranker
) -> None:
    """[SIG-006] both candidates have their own confirmed grape → keep."""
    decision, _ = _decide(
        [_shiraz(), _cab()], [*_OCR_CAB, "SHIRAZ"], settings, reranker
    )
    assert decision.text_leader == "agora-yachting-cabernet-sauvignon"
    assert decision.rerank_reason == "text_conflict"
    assert decision.slug == "agora-yachting-shiraz"


def test_max_img_drop_exceeded_keeps_top1(
    settings: OcrRerankSettings, reranker: FuzzyReranker
) -> None:
    """[SIG-006] leader cosine drop > max_img_drop → img_drop."""
    decision, _ = _decide(
        [_shiraz(0.60), _cab(0.55)], _OCR_CAB, settings, reranker, max_img_drop=0.02
    )
    assert decision.rerank_reason == "img_drop"
    assert decision.slug == "agora-yachting-shiraz"


def test_max_img_drop_within_limit_switches(
    settings: OcrRerankSettings, reranker: FuzzyReranker
) -> None:
    decision, _ = _decide(
        [_shiraz(0.60), _cab(0.58)], _OCR_CAB, settings, reranker, max_img_drop=0.05
    )
    assert decision.rerank_reason == "strong_text"


def test_margin_above_min_skips_ocr(
    settings: OcrRerankSettings, reranker: FuzzyReranker
) -> None:
    """[SIG-006] margin ≥ margin_min → OCR factory never called."""
    decision, factory = _decide(
        [_shiraz(0.70), _cab(0.60)], _OCR_CAB, settings, reranker
    )
    factory.assert_not_called()
    assert decision.rerank_triggered is False
    assert decision.rerank_reason is None
    assert decision.slug == "agora-yachting-shiraz"


@pytest.mark.parametrize(
    ("score_1", "expected"), [(0.95, 0.03), (0.80, 0.03), (0.70, 0.15), (0.40, 1.0)]
)
def test_prod_margin_tiers(
    settings: OcrRerankSettings, score_1: float, expected: float
) -> None:
    """[OCR-TIERS] high → 0.03; medium → 0.15; low → always OCR."""
    assert settings.policy.margin_min_for(score_1) == pytest.approx(expected)


def test_margin_tiers_fall_back_to_margin_min(settings: OcrRerankSettings) -> None:
    policy = settings.policy.model_copy(
        update={"margin_tiers": [{"min_score": 0.8, "margin_min": 0.03}]}
    )
    policy = type(policy).model_validate(policy.model_dump())
    assert policy.margin_min_for(0.5) == pytest.approx(policy.margin_min)


def test_medium_confidence_tier_triggers_ocr(
    settings: OcrRerankSettings, reranker: FuzzyReranker
) -> None:
    """[OCR-TIERS] gap 0.10 at score_1 0.70 → OCR (medium 0.15), not at 0.90."""
    medium, factory = _decide(
        [_shiraz(0.70), _cab(0.60)], _OCR_CAB, settings, reranker,
        margin_tiers=settings.policy.margin_tiers,
    )
    assert medium.rerank_triggered is True
    factory.assert_called_once()
    high, factory = _decide(
        [_shiraz(0.90), _cab(0.80)], _OCR_CAB, settings, reranker,
        margin_tiers=settings.policy.margin_tiers,
    )
    assert high.rerank_triggered is False
    factory.assert_not_called()


_GOLUBITSKOE = "Поместье Голубицкое"
_OCR_RED_BLEND = ["GOLUBITSKOE", "ESTATE -", "RED", "BLEND", "2023"]


def _colored(
    wine_id: int, slug: str, score: float, category: str, maker: str = _GOLUBITSKOE
) -> RankedHit:
    return RankedHit(
        wine_id=wine_id,
        slug=slug,
        score=score,
        title=slug.replace("-", " ").title(),
        manufacturer=maker,
        category=category,
        image_path=f"/static/wines/{slug}.webp",
        grape_variety="Каберне Совиньон",
    )


def _red_blend_hits() -> list[RankedHit]:
    return [
        _colored(1, "roze-blend", 0.78, "Розовое"),
        _colored(2, "pino-nuar-rozovoe", 0.66, "Розовое", maker="Другая"),
        _colored(3, "red-blend", 0.62, "Красное"),
    ]


def test_color_mismatch_switches_to_label_color(
    settings: OcrRerankSettings, reranker: FuzzyReranker
) -> None:
    """[OCR-COLOR] RED on a rosé winner → best red hit with confirmed producer."""
    decision, _ = _decide(
        _red_blend_hits(), _OCR_RED_BLEND, settings, reranker,
        margin_tiers=settings.policy.margin_tiers,
    )
    assert decision.slug == "red-blend"
    assert decision.rerank_reason == "color_mismatch"
    assert decision.evidence["_color"] == {"label": "Красное", "replaced": "roze-blend"}


def test_color_rule_needs_confirmed_manufacturer(
    settings: OcrRerankSettings, reranker: FuzzyReranker
) -> None:
    """[OCR-COLOR] red candidate of another producer → keep the image winner."""
    hits = _red_blend_hits()
    hits[2] = _colored(3, "red-blend", 0.62, "Красное", maker="Фанагория")
    decision, _ = _decide(
        hits, _OCR_RED_BLEND, settings, reranker,
        margin_tiers=settings.policy.margin_tiers,
    )
    assert decision.slug == "roze-blend"
    assert decision.rerank_reason != "color_mismatch"


def test_color_rule_off_or_matching_color(
    settings: OcrRerankSettings, reranker: FuzzyReranker
) -> None:
    off, _ = _decide(
        _red_blend_hits(), _OCR_RED_BLEND, settings, reranker, color_synonyms={},
        margin_tiers=settings.policy.margin_tiers,
    )
    assert off.slug == "roze-blend"
    rose, _ = _decide(
        _red_blend_hits(), ["GOLUBITSKOE", "ROSE", "BLEND"], settings, reranker,
        margin_tiers=settings.policy.margin_tiers,
    )
    assert rose.slug == "roze-blend"
    assert rose.rerank_reason != "color_mismatch"


def test_decision_log_contains_confident_fields(
    settings: OcrRerankSettings, reranker: FuzzyReranker, tmp_path: Path
) -> None:
    """[SIG-006] rerank_reason / text_leader / evidence + extra land in JSONL."""
    decision, _ = _decide([_shiraz(), _cab()], _OCR_CAB, settings, reranker)
    log_settings = settings.decision_log.model_copy(
        update={"path": str(tmp_path / "decisions.jsonl")}
    )
    emit_decision_log(
        decision,
        log_settings=log_settings,
        policy=settings.policy,
        ocr=settings.ocr,
        latency_ms={"total": 1.0},
        extra={"encoder_model": "siglip2_wine_p1_epoch_3.onnx", "embedding_dim": 1152},
    )
    lines = (tmp_path / "decisions.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["rerank_reason"] == "strong_text"
    assert record["text_leader"] == "agora-yachting-cabernet-sauvignon"
    assert record["evidence"]["agora-yachting-cabernet-sauvignon"]["grapes"] == [
        "каберне совиньон"
    ]
    assert record["encoder_model"] == "siglip2_wine_p1_epoch_3.onnx"
    assert record["embedding_dim"] == 1152


# --- label_evidence edge cases ----------------------------------------------


def test_multiword_grape_needs_all_tokens(reranker: FuzzyReranker) -> None:
    """[SIG-006] «Пино Гри»: OCR «ПИНО» only → no grape; both → grape."""
    kwargs = {
        "title": "Фанагория Пино Гри",
        "manufacturer": "Фанагория",
        "grape_variety": "Пино Гри",
    }
    assert reranker.label_evidence(["ПИНО"], **kwargs).grapes == []
    assert reranker.label_evidence(["ПИНО", "ГРИ"], **kwargs).grapes == ["пино гри"]


def test_vintage_digits_never_brand(reranker: FuzzyReranker) -> None:
    """[SIG-006] digits (vintage) never count as brand."""
    ev = reranker.label_evidence(
        ["2019"], title="Агора 2019 Резерв", manufacturer=_AGORA, grape_variety="Шираз"
    )
    assert ev.brand == []


@pytest.mark.parametrize(
    ("line", "manufacturer"),
    [
        ("ВИНОДЕЛЬНЯ", "Винодельня Фанагория"),
        ("ESTATE", "Golubitskoe Estate"),
        ("ПОМЕСТЬЕ", "Поместье Голубицкое"),
    ],
)
def test_producer_stopword_alone_does_not_confirm(
    reranker: FuzzyReranker, line: str, manufacturer: str
) -> None:
    """[SIG-006] «Винодельня» / «Estate» alone do not confirm manufacturer."""
    ev = reranker.label_evidence(
        [line], title="Резерв", manufacturer=manufacturer, grape_variety="Шираз"
    )
    assert ev.manufacturer is False


def test_producer_core_word_still_confirms(reranker: FuzzyReranker) -> None:
    ev = reranker.label_evidence(
        ["ФАНАГОРИЯ"],
        title="Резерв",
        manufacturer="Винодельня Фанагория",
        grape_variety="Шираз",
    )
    assert ev.manufacturer is True


def test_latin_ocr_confirms_cyrillic_producer(reranker: FuzzyReranker) -> None:
    """[SIG-006] GOLUBITSKOE confirms «Поместье Голубицкое»."""
    ev = reranker.label_evidence(
        ["GOLUBITSKOE"],
        title="Rose",
        manufacturer="Поместье Голубицкое",
        grape_variety="Шардоне",
    )
    assert ev.manufacturer is True
