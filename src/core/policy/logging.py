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

# Console summary only; the JSONL record keeps the full list.
_SUMMARY_OCR_LINES = 8


def summary_line(record: dict[str, Any]) -> str:
    """Одна строка для консоли: топ-K со score, решение, OCR, аналоги, время."""
    parts = [f"search {record.get('endpoint') or 'eval'}"]
    if record.get("search_id"):
        parts.append(f"id={record['search_id']}")
    if record.get("status"):
        parts.append(f"status={record['status']}")
    parts.append(f"winner={record.get('winner')}")
    parts.append(f"rerank={record.get('rerank_reason') or '-'}")
    top = " | ".join(f"{hit['slug']} {hit['score']:.3f}" for hit in record["top_k"])
    parts.append(f"top{len(record['top_k'])}=[{top}]")
    ocr = record.get("analogs_ocr_lines") or record.get("ocr_lines")
    if ocr:
        shown = json.dumps(ocr[:_SUMMARY_OCR_LINES], ensure_ascii=False)
        parts.append(f"ocr={shown}")
    hints = record.get("analogs_hints")
    if hints is not None:
        parts.append(
            f"analogs(grape={record.get('analogs_grape') or '-'}, "
            f"total={record.get('analogs_total')}, "
            f"manufacturer={hints.get('manufacturer') or '-'})"
        )
    total_ms = record.get("latency_ms", {}).get("total")
    if total_ms is not None:
        parts.append(f"{total_ms:.0f}ms")
    return " ".join(parts)


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
        "score_1": decision.score_1,
        "score_2": decision.score_2,
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
    logger.info("%s", summary_line(record))

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        logger.exception("failed to write decision log to %s", path)
