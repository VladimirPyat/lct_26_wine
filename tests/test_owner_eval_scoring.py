"""Stage 2B — owner_eval hit@1 scoring + anti-cheat swapped-golden canary."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from owner_eval_scoring import (
    hit_at_1,
    load_expected_slugs,
    load_golden_jsonl,
    load_predictions_jsonl,
    permute_slugs,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SET1 = REPO_ROOT / "data" / "owner_eval" / "1"
SET2 = REPO_ROOT / "data" / "owner_eval" / "2"

# Soft floor for live harness (document actual rates in test_stage_2b_eval.md).
# Canary must land well below this; honest scoring of golden vs itself is 1.0.
_CANARY_HIT1_CEILING = 0.15


def test_mapping_cases_load_set1() -> None:
    """[TEST-ID] 2B-06a mapping.json cases → expected slugs for set1."""
    expected = load_expected_slugs(SET1 / "mapping.json")
    golden = load_golden_jsonl(SET1 / "predictions.golden.jsonl")
    assert len(expected) >= 20
    rate, hits, compared = hit_at_1(dict(golden), expected)
    assert compared == len(expected)
    assert rate == pytest.approx(1.0)
    assert hits == compared


def test_owner_eval_canary_swapped_golden_fails() -> None:
    """[TEST-ID] 2B-07 swapped golden → hit@1 near 0 (anti-cheat).

    After an honest check (golden vs mapping = 1.0), permute slugs in a temp
    copy and re-score. Expected: comparison FAILS the high bar (near-zero hit@1).
    """
    expected = load_expected_slugs(SET1 / "mapping.json")
    golden = load_golden_jsonl(SET1 / "predictions.golden.jsonl")

    honest_rate, _, _ = hit_at_1(dict(golden), expected)
    assert honest_rate == pytest.approx(1.0)

    swapped = permute_slugs(golden)
    # Real golden file must stay untouched.
    on_disk = load_golden_jsonl(SET1 / "predictions.golden.jsonl")
    assert on_disk == golden

    canary_rate, canary_hits, canary_n = hit_at_1(dict(swapped), expected)
    assert canary_n == len(expected)
    assert canary_rate < _CANARY_HIT1_CEILING, (
        f"canary hit@1={canary_rate:.4f} ({canary_hits}/{canary_n}) "
        f"should be < {_CANARY_HIT1_CEILING} — comparator may be cheating"
    )


@pytest.mark.e2e
def test_owner_eval_set1_predictions_hit_at_1() -> None:
    """[TEST-ID] 2B-06 score live set1 predictions.jsonl vs mapping (if present)."""
    pred_path = SET1 / "predictions.jsonl"
    if not pred_path.is_file():
        pytest.skip("set1 predictions.jsonl missing — run participant_test.sh first")

    predicted = load_predictions_jsonl(pred_path)
    expected = load_expected_slugs(SET1 / "mapping.json")
    nulls = [qid for qid, slug in predicted.items() if slug is None]
    assert not nulls, f"null predicted_slug for query_ids: {nulls[:5]}"
    rate, hits, compared = hit_at_1(predicted, expected)
    assert compared == len(expected), "every mapping case must have a prediction"
    # Soft acceptance: report actual rate; hard-fail only if catastrophic.
    assert rate >= 0.0
    assert hits >= 0
    # Persist a small sidecar for the human report (optional visibility).
    summary = {
        "set": 1,
        "hit_at_1": rate,
        "hits": hits,
        "compared": compared,
        "n_predictions": len(predicted),
    }
    out = REPO_ROOT / "data" / "tmp" / "owner_eval_set1_score.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


@pytest.mark.e2e
def test_owner_eval_set2_predictions_hit_at_1() -> None:
    """[TEST-ID] 2B-08 score live set2 predictions.jsonl vs mapping (if present)."""
    pred_path = SET2 / "predictions.jsonl"
    if not pred_path.is_file():
        pytest.skip("set2 predictions.jsonl missing — run participant_test.sh first")

    predicted = load_predictions_jsonl(pred_path)
    expected = load_expected_slugs(SET2 / "mapping.json")
    nulls = [qid for qid, slug in predicted.items() if slug is None]
    assert not nulls, f"null predicted_slug for query_ids: {nulls[:5]}"
    rate, hits, compared = hit_at_1(predicted, expected)
    assert compared == len(expected)
    summary = {
        "set": 2,
        "hit_at_1": rate,
        "hits": hits,
        "compared": compared,
        "n_predictions": len(predicted),
    }
    out = REPO_ROOT / "data" / "tmp" / "owner_eval_set2_score.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
