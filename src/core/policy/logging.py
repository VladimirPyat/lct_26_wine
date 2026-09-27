"""Append structured eval decision records as JSON lines."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.config import DecisionLogSettings, OcrSettings, PolicySettings
from core.policy.decision import PolicyDecision

logger = logging.getLogger(__name__)


def emit_decision_log(
    decision: PolicyDecision,
    *,
    log_settings: DecisionLogSettings,
    policy: PolicySettings,
    ocr: OcrSettings,
    latency_ms: dict[str, float],
    repo_root: Path | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Write one JSONL record; never raise into the HTTP path on I/O failure."""
    root = repo_root if repo_root is not None else Path(__file__).resolve().parents[3]
    path = Path(log_settings.path)
    if not path.is_absolute():
        path = root / path

    top_k = [
        {"slug": hit["slug"], "score": hit["score"], "wine_id": hit["wine_id"]}
        for hit in decision.hits
    ]
    ocr_lines = decision.ocr_lines[: log_settings.ocr_lines_cap]
    record: dict[str, Any] = {
        "ts": datetime.now(UTC).isoformat(),
        "top_k": top_k,
        "margin": decision.margin,
        "abs_min": policy.abs_min,
        "margin_min": policy.margin_min,
        "garbage": decision.garbage,
        "enable_rerank": decision.enable_rerank,
        "rerank_triggered": decision.rerank_triggered,
        "ocr_engine": ocr.engine,
        "ocr_llm_task": ocr.llm_task if ocr.engine == "llm" else None,
        "ocr_lines": ocr_lines,
        "winner_before_rerank": decision.winner_before_rerank,
        "winner_after_rerank": decision.winner_after_rerank,
        "winner": decision.slug,
        "rerank_mode": policy.rerank_mode,
        "rerank_reason": decision.rerank_reason,
        "text_leader": decision.text_leader,
        "text_scores": decision.text_scores,
        "evidence": decision.evidence,
        "latency_ms": latency_ms,
    }
    if extra:
        record.update(extra)

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        logger.exception("failed to write decision log to %s", path)
