"""Eval decision policy: margin / abs_min / optional OCR+fuzzy rerank."""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from core.config import PolicySettings
from core.contracts import RankedHit, SearchResult, WineRecord
from core.ocr.base import IOCREngine
from core.text.fuzzy import FuzzyReranker


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


def decide(
    hits: Sequence[RankedHit],
    *,
    crop_path: str,
    policy: PolicySettings,
    ocr_factory: Callable[[], IOCREngine],
    reranker: FuzzyReranker,
    rerank_top: int,
) -> PolicyDecision:
    """Pick always-a-slug winner when ``hits`` is non-empty.

    OCR is created via ``ocr_factory`` only when rerank runs (lazy), so
    ``enable_rerank: false`` never loads PHOCR/LLM.
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

    if skip_rerank:
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
        )

    ocr = ocr_factory()
    t0 = time.perf_counter()
    lines = ocr.recognize(crop_path)
    latency["ocr"] = (time.perf_counter() - t0) * 1000.0

    candidates = [_hit_to_search_result(hit) for hit in hits]
    wines_by_id = {hit["wine_id"]: _hit_to_wine_record(hit) for hit in hits}
    pool = min(rerank_top, len(candidates), policy.top_k)

    t1 = time.perf_counter()
    reranked = reranker.rerank(lines, candidates, wines_by_id, top_n=pool)
    latency["rerank"] = (time.perf_counter() - t1) * 1000.0

    if not reranked:
        winner = winner_before
    else:
        best_id = reranked[0]["wine_id"]
        winner = next(
            (hit["slug"] for hit in hits if hit["wine_id"] == best_id),
            winner_before,
        )

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
    )


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
