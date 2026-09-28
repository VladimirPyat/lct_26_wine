"""PROD-API A — статус / уровень уверенности по score_1 (чистая функция)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.config import ConfidenceSettings
from core.product.catalog_service import classify_confidence

# Test-local thresholds, deliberately not the prod product.yaml values.
T = ConfidenceSettings(high_min=0.9, medium_min=0.7, not_found_min=0.4)


@pytest.mark.parametrize(
    ("score", "status", "level"),
    [
        (0.0, "not_found", "low"),
        (0.3999, "not_found", "low"),
        (0.4, "low", "low"),
        (0.6999, "low", "low"),
        (0.7, "found", "medium"),
        (0.8999, "found", "medium"),
        (0.9, "found", "high"),
        (1.0, "found", "high"),
    ],
)
def test_status_boundaries_inclusive(score: float, status: str, level: str) -> None:
    """[TEST-ID] PA-A5 границы not_found_min / medium_min / high_min (≥)."""
    assert classify_confidence(score, T) == (status, level)


def test_status_equal_thresholds_collapse() -> None:
    """[TEST-ID] PA-A5b равные пороги допустимы: нет полосы low/medium."""
    t = ConfidenceSettings(high_min=0.6, medium_min=0.6, not_found_min=0.6)
    assert classify_confidence(0.5999, t) == ("not_found", "low")
    assert classify_confidence(0.6, t) == ("found", "high")


@pytest.mark.parametrize(
    ("high", "medium", "not_found"),
    [
        (0.7, 0.8, 0.5),  # medium > high
        (0.9, 0.6, 0.7),  # not_found > medium
        (0.5, 0.6, 0.7),  # fully reversed
    ],
)
def test_validator_rejects_unordered(
    high: float, medium: float, not_found: float
) -> None:
    """[TEST-ID] PA-A6 валидатор отклоняет неупорядоченные пороги."""
    with pytest.raises(ValidationError):
        ConfidenceSettings(high_min=high, medium_min=medium, not_found_min=not_found)
