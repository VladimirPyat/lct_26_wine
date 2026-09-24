"""Helpers to score owner_eval predictions vs mapping / golden."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_expected_slugs(mapping_path: Path) -> dict[str, str]:
    """Load query_id → expected slug from owner_eval mapping.json (cases list)."""
    raw: Any = json.loads(mapping_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or "cases" not in raw:
        msg = f"expected mapping.json with 'cases': {mapping_path}"
        raise ValueError(msg)
    expected: dict[str, str] = {}
    for case in raw["cases"]:
        if not isinstance(case, dict):
            continue
        qid = case.get("query_id")
        slug = case.get("expected_slug")
        if isinstance(qid, str) and isinstance(slug, str) and slug:
            expected[qid] = slug
    return expected


def load_predictions_jsonl(path: Path) -> dict[str, str | None]:
    """Load query_id → predicted_slug (None if missing/null)."""
    out: dict[str, str | None] = {}
    with path.open(encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            obj = json.loads(line)
            qid = str(obj["query_id"])
            slug = obj.get("predicted_slug")
            out[qid] = slug if isinstance(slug, str) and slug else None
    return out


def load_golden_jsonl(path: Path) -> dict[str, str]:
    """Load query_id → predicted_slug from predictions.golden.jsonl."""
    out: dict[str, str] = {}
    with path.open(encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            obj = json.loads(line)
            qid = str(obj["query_id"])
            slug = obj.get("predicted_slug")
            if isinstance(slug, str) and slug:
                out[qid] = slug
    return out


def hit_at_1(
    predicted: dict[str, str | None],
    expected: dict[str, str],
) -> tuple[float, int, int]:
    """Return (rate, hits, compared) for overlapping query_ids with non-null preds."""
    hits = 0
    compared = 0
    for qid, gold in expected.items():
        pred = predicted.get(qid)
        if pred is None:
            continue
        compared += 1
        if pred == gold:
            hits += 1
    rate = (hits / compared) if compared else 0.0
    return rate, hits, compared


def permute_slugs(golden: dict[str, str]) -> dict[str, str]:
    """Rotate predicted_slug values so almost no query keeps the correct slug."""
    items = list(golden.items())
    if len(items) < 2:
        msg = "need at least 2 golden rows to permute"
        raise ValueError(msg)
    slugs = [slug for _, slug in items]
    rotated = slugs[1:] + slugs[:1]
    return {qid: rotated[i] for i, (qid, _) in enumerate(items)}
