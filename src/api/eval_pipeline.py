"""Eval predict orchestrator: retrieve → policy → decision log."""

from __future__ import annotations

import time
from pathlib import Path

from api.runtime import EvalRuntime
from core.policy.decision import PolicyDecision, decide
from core.policy.logging import emit_decision_log
from core.retrieve.retriever import WineRetriever
from db.repository import WineRepository
from db.session import session_scope


class EmptyCatalogError(RuntimeError):
    """pgvector returned no hits (empty catalog or hard retrieval failure)."""


def predict_slug(runtime: EvalRuntime, image_path: str | Path) -> str:
    """Run full eval pipeline; always return a non-empty slug when hits exist."""
    path = Path(image_path)
    if not path.is_file():
        msg = f"Image not found for eval predict: {path}"
        raise FileNotFoundError(msg)

    policy = runtime.ocr_rerank.policy
    t_total = time.perf_counter()

    with session_scope(runtime.session_factory) as session:
        repository = WineRepository(session)
        retriever = WineRetriever(runtime.cropper, runtime.encoder, repository)
        bundle = retriever.retrieve_bundle(str(path), top_k=policy.top_k)

        if not bundle.hits:
            msg = "catalog search returned no hits (empty wines table?)"
            raise EmptyCatalogError(msg)

        decision = decide(
            bundle.hits,
            crop_path=bundle.crop_path,
            policy=policy,
            ocr_factory=runtime.get_ocr,
            reranker=runtime.reranker,
            rerank_top=min(runtime.ocr_rerank.rerank_top, policy.top_k),
        )

    total_ms = (time.perf_counter() - t_total) * 1000.0
    latency_ms = {
        **bundle.latency_ms,
        **decision.latency_ms,
        "total": total_ms,
    }
    _log_decision(runtime, decision, latency_ms)
    return decision.slug


def _log_decision(
    runtime: EvalRuntime,
    decision: PolicyDecision,
    latency_ms: dict[str, float],
) -> None:
    emit_decision_log(
        decision,
        log_settings=runtime.ocr_rerank.decision_log,
        policy=runtime.ocr_rerank.policy,
        ocr=runtime.ocr_rerank.ocr,
        latency_ms=latency_ms,
        repo_root=runtime.repo_root,
    )
