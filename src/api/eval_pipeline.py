"""Shared search pipeline: retrieve → policy → decision log (eval + product)."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from api.runtime import EvalRuntime
from core.policy.decision import PolicyDecision, decide
from core.policy.logging import emit_decision_log
from core.retrieve.retriever import RetrieveBundle, WineRetriever
from db.repository import WineRepository
from db.session import session_scope

# ONNX / OCR sessions are shared; product routes run in a threadpool.
_PIPELINE_LOCK = threading.Lock()


class EmptyCatalogError(RuntimeError):
    """pgvector returned no hits (empty catalog or hard retrieval failure)."""


@dataclass(frozen=True)
class SearchRun:
    """Результат общего пайплайна: кандидаты, решение политики, задержки (мс)."""

    bundle: RetrieveBundle
    decision: PolicyDecision
    latency_ms: dict[str, float]


def run_search(
    runtime: EvalRuntime,
    image_path: str | Path,
    *,
    log_fields: Callable[[PolicyDecision], Mapping[str, object]] | None = None,
) -> SearchRun:
    """Прогнать фото через retrieve → decide и записать строку decision log.

    ``log_fields`` добавляет поля в запись лога (например, статус продукта),
    вычисленные по готовому решению. Пустой каталог → ``EmptyCatalogError``.
    """
    path = Path(image_path)
    if not path.is_file():
        msg = f"Image not found for search: {path}"
        raise FileNotFoundError(msg)

    policy = runtime.ocr_rerank.policy
    t_total = time.perf_counter()

    with _PIPELINE_LOCK, session_scope(runtime.session_factory) as session:
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
    extra: dict[str, object] = {
        "used_fallback": bundle.used_fallback,
        "crop_path": bundle.crop_path,
        "query_image": str(path),
        "encoder_model": runtime.encoder_model,
        "embedding_dim": runtime.encoder.embedding_dim,
    }
    if log_fields is not None:
        extra.update(log_fields(decision))
    _log_decision(runtime, decision, latency_ms, extra=extra)
    return SearchRun(bundle=bundle, decision=decision, latency_ms=latency_ms)


def recognize_crop(runtime: EvalRuntime, crop_path: str) -> list[str]:
    """OCR кропа этикетки (ленивый движок рантайма, под общим локом)."""
    with _PIPELINE_LOCK:
        return list(runtime.get_ocr().recognize(crop_path))


def predict_slug(runtime: EvalRuntime, image_path: str | Path) -> str:
    """Run full eval pipeline; always return a non-empty slug when hits exist."""
    return run_search(runtime, image_path).decision.slug


def _log_decision(
    runtime: EvalRuntime,
    decision: PolicyDecision,
    latency_ms: dict[str, float],
    *,
    extra: dict[str, object] | None = None,
) -> None:
    emit_decision_log(
        decision,
        log_settings=runtime.ocr_rerank.decision_log,
        policy=runtime.ocr_rerank.policy,
        ocr=runtime.ocr_rerank.ocr,
        latency_ms=latency_ms,
        repo_root=runtime.repo_root,
        extra=extra,
    )
