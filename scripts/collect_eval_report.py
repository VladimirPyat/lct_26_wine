"""Collect metrics from eval decision JSONL (+ optional mapping.json)."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any


def _percentile(sorted_values: Sequence[float], pct: float) -> float | None:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    rank = (pct / 100.0) * (len(sorted_values) - 1)
    low = int(math.floor(rank))
    high = int(math.ceil(rank))
    if low == high:
        return float(sorted_values[low])
    weight = rank - low
    return float(sorted_values[low] * (1.0 - weight) + sorted_values[high] * weight)


def load_decision_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as err:
                msg = f"{path}:{line_no}: invalid JSON: {err}"
                raise ValueError(msg) from err
            if not isinstance(obj, dict):
                msg = f"{path}:{line_no}: expected object, got {type(obj).__name__}"
                raise ValueError(msg)
            records.append(obj)
    return records


def load_mapping(path: Path) -> dict[str, str]:
    """Load ``query_id`` → expected slug from mapping.json or golden JSONL."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    mapping: dict[str, str] = {}
    if isinstance(raw, dict):
        # mapping.json: {query_id: slug} or {query_id: {slug: ...}}
        for key, value in raw.items():
            if isinstance(value, str):
                mapping[str(key)] = value
            elif isinstance(value, dict) and "slug" in value:
                mapping[str(key)] = str(value["slug"])
            elif isinstance(value, dict) and "predicted_slug" in value:
                mapping[str(key)] = str(value["predicted_slug"])
        return mapping
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            qid = item.get("query_id")
            slug = item.get("predicted_slug") or item.get("slug")
            if qid is not None and isinstance(slug, str):
                mapping[str(qid)] = slug
        return mapping
    msg = f"unsupported mapping format in {path}"
    raise ValueError(msg)


def load_predictions(path: Path) -> dict[str, str]:
    """Load ``query_id`` → ``predicted_slug`` from harness JSONL."""
    mapping: dict[str, str] = {}
    with path.open(encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as err:
                msg = f"{path}:{line_no}: invalid JSON: {err}"
                raise ValueError(msg) from err
            if not isinstance(obj, dict):
                continue
            qid = obj.get("query_id")
            slug = obj.get("predicted_slug")
            if qid is not None and isinstance(slug, str) and slug:
                mapping[str(qid)] = slug
    return mapping


def _hit_at_1(
    predicted: dict[str, str],
    expected: dict[str, str],
) -> tuple[float | None, int, int]:
    compared = 0
    hits = 0
    for qid, slug in predicted.items():
        gold = expected.get(qid)
        if gold is None:
            continue
        compared += 1
        if slug == gold:
            hits += 1
    if compared == 0:
        return None, 0, 0
    return hits / compared, compared, hits


def collect_report(
    records: Sequence[dict[str, Any]],
    *,
    mapping: dict[str, str] | None = None,
    predictions: dict[str, str] | None = None,
) -> dict[str, Any]:
    n = len(records)
    rerank_n = sum(1 for r in records if r.get("rerank_triggered") is True)
    garbage_n = sum(1 for r in records if r.get("garbage") is True)
    totals = [
        float(r["latency_ms"]["total"])
        for r in records
        if isinstance(r.get("latency_ms"), dict) and "total" in r["latency_ms"]
    ]
    totals_sorted = sorted(totals)

    hit_at_1: float | None = None
    compared = 0
    hits = 0
    if mapping and predictions:
        hit_at_1, compared, hits = _hit_at_1(predictions, mapping)
    elif mapping:
        # Fallback: decision log rows that carry query_id + winner.
        predicted_from_log: dict[str, str] = {}
        for record in records:
            qid = record.get("query_id")
            winner = record.get("winner")
            if qid is not None and isinstance(winner, str):
                predicted_from_log[str(qid)] = winner
        hit_at_1, compared, hits = _hit_at_1(predicted_from_log, mapping)

    return {
        "n_requests": n,
        "rerank_rate": (rerank_n / n) if n else None,
        "garbage_rate": (garbage_n / n) if n else None,
        "latency_ms": {
            "p50": _percentile(totals_sorted, 50),
            "p95": _percentile(totals_sorted, 95),
            "n": len(totals_sorted),
        },
        "hit_at_1": hit_at_1,
        "hit_at_1_compared": compared if mapping else None,
        "hit_at_1_hits": hits if mapping else None,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate eval decision JSONL: rerank/garbage rates, "
            "latency p50/p95, optional hit@1 vs mapping.json"
        )
    )
    parser.add_argument(
        "--log",
        required=True,
        type=Path,
        help="Path to decision JSONL (config decision_log.path)",
    )
    parser.add_argument(
        "--mapping",
        type=Path,
        default=None,
        help="Optional mapping.json or golden JSONL for hit@1",
    )
    parser.add_argument(
        "--predictions",
        type=Path,
        default=None,
        help="Optional harness predictions.jsonl (query_id + predicted_slug)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print report as a single JSON object",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if not args.log.is_file():
        print(f"ERROR: log not found: {args.log}", file=sys.stderr)
        return 1

    records = load_decision_records(args.log)
    mapping = load_mapping(args.mapping) if args.mapping is not None else None
    predictions = (
        load_predictions(args.predictions) if args.predictions is not None else None
    )
    report = collect_report(records, mapping=mapping, predictions=predictions)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"n_requests:   {report['n_requests']}")
        rr = report["rerank_rate"]
        gr = report["garbage_rate"]
        print(f"rerank_rate:  {rr:.4f}" if rr is not None else "rerank_rate:  n/a")
        print(f"garbage_rate: {gr:.4f}" if gr is not None else "garbage_rate: n/a")
        lat = report["latency_ms"]
        p50, p95 = lat["p50"], lat["p95"]
        print(
            f"latency_ms:   p50={p50:.1f} p95={p95:.1f} (n={lat['n']})"
            if p50 is not None and p95 is not None
            else "latency_ms:   n/a"
        )
        if report["hit_at_1"] is not None:
            print(
                f"hit@1:        {report['hit_at_1']:.4f} "
                f"({report['hit_at_1_hits']}/{report['hit_at_1_compared']})"
            )
        elif mapping is not None:
            print("hit@1:        n/a (no overlapping query_id/winner)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
