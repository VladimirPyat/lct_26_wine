"""Eval decision policy: margin / abs_min / optional OCR+fuzzy rerank."""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from core.config import PolicySettings
from core.contracts import RankedHit, SearchResult, WineRecord
from core.ocr.base import IOCREngine, OCRUnavailableError
from core.text.fuzzy import FuzzyReranker, LabelEvidence
from core.text.normalize import expand_token_aliases, normalize_text


@dataclass(frozen=True)
class PolicyDecision:
    """Winner slug plus structured fields for the decision log."""

    slug: str
    garbage: bool
    margin: float
    score_1: float
    score_2: float
    enable_rerank: bool
    rerank_triggered: bool
    winner_before_rerank: str
    winner_after_rerank: str | None
    ocr_lines: list[str]
    hits: list[RankedHit]
    latency_ms: dict[str, float] = field(default_factory=dict)
    rerank_reason: str | None = None
    text_leader: str | None = None
    text_scores: dict[str, float] = field(default_factory=dict)
    evidence: dict[str, dict[str, object]] = field(default_factory=dict)


def decide(
    hits: Sequence[RankedHit],
    *,
    crop_path: str,
    policy: PolicySettings,
    ocr_factory: Callable[[], IOCREngine | None],
    reranker: FuzzyReranker,
    rerank_top: int,
) -> PolicyDecision:
    """Pick always-a-slug winner when ``hits`` is non-empty.

    OCR is created via ``ocr_factory`` only when rerank runs (lazy), so
    ``enable_rerank: false`` never loads PHOCR/LLM. Factory returns ``None``
    (no OCR engine) → rerank skipped, ``rerank_reason="ocr_unavailable"``;
    ``OCRUnavailableError`` from ``recognize`` → ``rerank_reason="ocr_failed"``.
    Other OCR errors (PHOCR) propagate.

    ``rerank_mode: always`` — text leader wins. ``confident`` — text leader
    replaces image top-1 only when OCR confirms one of ``strong_combos`` for it
    (e.g. manufacturer + grape) with a grape/brand token that the image top-1
    does not have, and the image top-1 has no such distinguishing token itself.
    """
    if not hits:
        msg = "decision policy requires at least one RankedHit"
        raise ValueError(msg)

    score_1 = float(hits[0]["score"])
    score_2 = float(hits[1]["score"]) if len(hits) > 1 else score_1
    margin = score_1 - score_2
    garbage = score_1 < policy.abs_min
    winner_before = hits[0]["slug"]

    skip_rerank = (
        not policy.enable_rerank
        or margin >= policy.margin_min
        or len(hits) == 1
    )
    latency: dict[str, float] = {"ocr": 0.0, "rerank": 0.0}

    def no_rerank(reason: str | None) -> PolicyDecision:
        return PolicyDecision(
            slug=winner_before,
            garbage=garbage,
            margin=margin,
            score_1=score_1,
            score_2=score_2,
            enable_rerank=policy.enable_rerank,
            rerank_triggered=False,
            winner_before_rerank=winner_before,
            winner_after_rerank=None,
            ocr_lines=[],
            hits=list(hits),
            latency_ms=latency,
            rerank_reason=reason,
        )

    if skip_rerank:
        return no_rerank(None)

    ocr = ocr_factory()
    if ocr is None:
        return no_rerank("ocr_unavailable")
    t0 = time.perf_counter()
    try:
        lines = ocr.recognize(crop_path)
    except OCRUnavailableError:
        latency["ocr"] = (time.perf_counter() - t0) * 1000.0
        return no_rerank("ocr_failed")
    latency["ocr"] = (time.perf_counter() - t0) * 1000.0

    candidates = [_hit_to_search_result(hit) for hit in hits]
    wines_by_id = {hit["wine_id"]: _hit_to_wine_record(hit) for hit in hits}
    pool = min(rerank_top, len(candidates), policy.top_k)

    t1 = time.perf_counter()
    reranked = reranker.rerank(lines, candidates, wines_by_id, top_n=pool)
    by_id = {hit["wine_id"]: hit for hit in hits}
    leader = by_id.get(reranked[0]["wine_id"]) if reranked else None
    text_scores = {
        by_id[item["wine_id"]]["slug"]: float(dict(item).get("text_score", 0.0))
        for item in reranked
        if item["wine_id"] in by_id
    }

    evidence: dict[str, dict[str, object]] = {}
    if leader is None:
        winner, reason = winner_before, "no_text_leader"
    elif policy.rerank_mode == "always":
        winner, reason = leader["slug"], "always"
    else:
        winner, reason, evidence = _confident_winner(
            hits[0], leader, lines, reranker, policy
        )
    latency["rerank"] = (time.perf_counter() - t1) * 1000.0

    return PolicyDecision(
        slug=winner,
        garbage=garbage,
        margin=margin,
        score_1=score_1,
        score_2=score_2,
        enable_rerank=policy.enable_rerank,
        rerank_triggered=True,
        winner_before_rerank=winner_before,
        winner_after_rerank=winner,
        ocr_lines=list(lines),
        hits=list(hits),
        latency_ms=latency,
        rerank_reason=reason,
        text_leader=leader["slug"] if leader else None,
        text_scores=text_scores,
        evidence=evidence,
    )


def _confident_winner(
    image_top: RankedHit,
    leader: RankedHit,
    lines: Sequence[str],
    reranker: FuzzyReranker,
    policy: PolicySettings,
) -> tuple[str, str, dict[str, dict[str, object]]]:
    """Return (winner slug, reason, evidence log) for ``rerank_mode: confident``."""
    keep = image_top["slug"]
    if leader["wine_id"] == image_top["wine_id"]:
        return keep, "text_agrees", {}

    ev_leader = _evidence(reranker, lines, leader)
    ev_top = _evidence(reranker, lines, image_top)
    log = {leader["slug"]: ev_leader.as_log(), keep: ev_top.as_log()}

    if not _is_strong(ev_leader, policy.strong_combos):
        return keep, "weak_text", log
    if not _distinguishing(ev_leader, ev_top):
        return keep, "not_distinguishing", log
    if _distinguishing(ev_top, ev_leader):
        return keep, "text_conflict", log
    drop = float(image_top["score"]) - float(leader["score"])
    if policy.max_img_drop is not None and drop > policy.max_img_drop:
        return keep, "img_drop", log
    return leader["slug"], "strong_text", log


def _evidence(
    reranker: FuzzyReranker, lines: Sequence[str], hit: RankedHit
) -> LabelEvidence:
    return reranker.label_evidence(
        lines,
        title=hit["title"],
        manufacturer=hit["manufacturer"],
        grape_variety=hit.get("grape_variety", ""),
    )


def _is_strong(ev: LabelEvidence, combos: Sequence[Sequence[str]]) -> bool:
    signals = ev.signals()
    return any(set(combo) <= signals for combo in combos)


def _distinguishing(ev: LabelEvidence, other: LabelEvidence) -> bool:
    """True if ``ev`` has an OCR-confirmed grape / brand token absent from ``other``."""
    other_grapes = {normalize_text(name) for name in other.grape_names}
    if any(normalize_text(name) not in other_grapes for name in ev.grapes):
        return True
    return any(not (expand_token_aliases(t) & other.title_tokens) for t in ev.brand)


def _hit_to_search_result(hit: RankedHit) -> SearchResult:
    return SearchResult(
        wine_id=hit["wine_id"],
        external_id=hit["wine_id"],
        score=hit["score"],
        inliers=None,
        good_matches=None,
        vlad_rank=None,
        image_path=hit["image_path"],
    )


def _hit_to_wine_record(hit: RankedHit) -> WineRecord:
    return WineRecord(
        id=hit["wine_id"],
        external_id=hit["wine_id"],
        title=hit["title"],
        manufacturer=hit["manufacturer"],
        category=hit["category"],
        region="",
        color="",
        slug=hit["slug"],
        image_path=hit["image_path"],
        product_url=None,
        faiss_row=None,
    )
