"""ORM models for wine catalog lookups and ``wines`` (pgvector)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    DateTime,
    Double,
    ForeignKey,
    Numeric,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.config import load_database_settings
from db.base import Base

_EMBEDDING_DIM: int = load_database_settings().embedding_dim


class Category(Base):
    """Color / type lookup (owner CSV «Категория»)."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)

    wines: Mapped[list[Wine]] = relationship(back_populates="category")


class Region(Base):
    """Region lookup (owner CSV «Регион»)."""

    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)

    wines: Mapped[list[Wine]] = relationship(back_populates="region")


class SweetnessLevel(Base):
    """Site-style dryness / sweetness lookup."""

    __tablename__ = "sweetness_levels"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)

    wines: Mapped[list[Wine]] = relationship(back_populates="sweetness")


class Wine(Base):
    """Catalog row: metadata + DINO embedding."""

    __tablename__ = "wines"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    category_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("categories.id"), nullable=False
    )
    color: Mapped[str] = mapped_column(Text, nullable=False)
    region_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("regions.id"), nullable=False
    )
    grape_variety: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    manufacturer: Mapped[str] = mapped_column(Text, nullable=False)
    public_rating: Mapped[float | None] = mapped_column(Double, nullable=True)
    product_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    serving_temperature: Mapped[str | None] = mapped_column(Text, nullable=True)
    alcohol_pct: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)
    dishes: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    sweetness_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("sweetness_levels.id"), nullable=True
    )
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(_EMBEDDING_DIM), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    modified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    category: Mapped[Category] = relationship(back_populates="wines")
    region: Mapped[Region] = relationship(back_populates="wines")
    sweetness: Mapped[SweetnessLevel | None] = relationship(back_populates="wines")
