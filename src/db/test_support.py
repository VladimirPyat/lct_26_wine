"""Helpers for inserting catalog wines in tests (Stage 1.1).

Prefer real DINO embeddings via ``core.retrieve.encode_image`` on a local image
under ``data/owner_database/images/`` (or a tiny file in ``tests/fixtures/``).
For pure SQL unit tests, pass a precomputed vector of length ``embedding_dim``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.config import load_database_settings
from db.models import Category, Region, SweetnessLevel, Wine
from db.repository import WineRepository

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SAMPLE_IMAGE = (
    _REPO_ROOT
    / "data"
    / "owner_database"
    / "images"
    / "massandra-rozovoe-suhoe.webp"
)


def get_or_create_category(session: Session, name: str) -> Category:
    row = session.scalars(select(Category).where(Category.name == name)).one_or_none()
    if row is not None:
        return row
    row = Category(name=name)
    session.add(row)
    session.flush()
    return row


def get_or_create_region(session: Session, name: str) -> Region:
    row = session.scalars(select(Region).where(Region.name == name)).one_or_none()
    if row is not None:
        return row
    row = Region(name=name)
    session.add(row)
    session.flush()
    return row


def get_sweetness_by_name(session: Session, name: str) -> SweetnessLevel | None:
    return session.scalars(
        select(SweetnessLevel).where(SweetnessLevel.name == name)
    ).one_or_none()


def zero_embedding(*, dim: int | None = None) -> list[float]:
    """Deterministic zero vector of configured catalog dim (SQL-only smoke)."""
    size = dim if dim is not None else load_database_settings().embedding_dim
    return [0.0] * size


def unit_embedding(index: int, *, dim: int | None = None) -> list[float]:
    """One-hot-like unit vector for orthogonal ranking smoke tests."""
    size = dim if dim is not None else load_database_settings().embedding_dim
    if index < 0 or index >= size:
        msg = f"unit embedding index out of range: {index} (dim={size})"
        raise ValueError(msg)
    vector = [0.0] * size
    vector[index] = 1.0
    return vector


def insert_wine_with_embedding(
    session: Session,
    *,
    slug: str,
    title: str,
    embedding: Sequence[float],
    category_name: str = "Красное",
    region_name: str = "Кубань",
    color: str = "красное",
    grape_variety: str = "н/д",
    description: str = "н/д",
    manufacturer: str = "н/д",
    image_url: str | None = None,
    sweetness_name: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> Wine:
    """Insert a wine with required fields + embedding; get-or-create lookups.

    Does not commit — caller owns the transaction.
    """
    expected_dim = load_database_settings().embedding_dim
    if len(embedding) != expected_dim:
        msg = (
            f"embedding length {len(embedding)} != configured embedding_dim "
            f"{expected_dim}"
        )
        raise ValueError(msg)

    category = get_or_create_category(session, category_name)
    region = get_or_create_region(session, region_name)
    sweetness_id: int | None = None
    if sweetness_name is not None:
        sweetness = get_sweetness_by_name(session, sweetness_name)
        if sweetness is None:
            msg = f"unknown sweetness_levels.name: {sweetness_name!r}"
            raise ValueError(msg)
        sweetness_id = sweetness.id

    fields: dict[str, Any] = {
        "slug": slug,
        "title": title,
        "category_id": category.id,
        "color": color,
        "region_id": region.id,
        "grape_variety": grape_variety,
        "description": description,
        "manufacturer": manufacturer,
        "image_url": image_url or f"/static/wines/{slug}.webp",
        "embedding": list(embedding),
        "sweetness_id": sweetness_id,
    }
    if extra:
        fields.update(dict(extra))

    return WineRepository(session).create(fields)
