"""Wine catalog repository (CRUD, slug, filters, pgvector top-K)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, joinedload

from core.contracts import RankedHit
from db.models import Category, Region, SweetnessLevel, Wine

_WINE_LOAD = (
    joinedload(Wine.category),
    joinedload(Wine.region),
    joinedload(Wine.sweetness),
)


class WineRepository:
    """SQLAlchemy API for ``wines`` + lookup joins (Stage 1 contract).

    Vector score: ``score = 1 - cosine_distance(embedding, query)`` (higher better).
    Embeddings are expected L2-normalized (DINO encoder default).

    ``get_many_by_ids`` preserves the order of the input ``ids`` sequence.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, wine_fields: Mapping[str, Any]) -> Wine:
        """Insert a wine row; caller supplies FK ids + embedding + required fields."""
        wine = Wine(**dict(wine_fields))
        self._session.add(wine)
        self._session.flush()
        self._session.refresh(wine)
        return self._reload(wine.id)  # type: ignore[return-value]

    def get_by_id(self, wine_id: int) -> Wine | None:
        stmt = select(Wine).options(*_WINE_LOAD).where(Wine.id == wine_id)
        return self._session.scalars(stmt).unique().one_or_none()

    def update(self, wine_id: int, fields: Mapping[str, Any]) -> Wine | None:
        wine = self._session.get(Wine, wine_id)
        if wine is None:
            return None
        for key, value in fields.items():
            if key == "id":
                msg = "cannot update wine primary key"
                raise ValueError(msg)
            setattr(wine, key, value)
        wine.modified_at = datetime.now(UTC)
        self._session.flush()
        return self._reload(wine_id)

    def delete(self, wine_id: int) -> bool:
        """Hard delete. Returns True if a row was removed."""
        wine = self._session.get(Wine, wine_id)
        if wine is None:
            return False
        self._session.delete(wine)
        self._session.flush()
        return True

    def list(self, *, limit: int, offset: int) -> list[Wine]:
        stmt = (
            select(Wine)
            .options(*_WINE_LOAD)
            .order_by(Wine.id)
            .limit(limit)
            .offset(offset)
        )
        return list(self._session.scalars(stmt).unique().all())

    def get_by_slug(self, slug: str) -> Wine | None:
        stmt = select(Wine).options(*_WINE_LOAD).where(Wine.slug == slug)
        return self._session.scalars(stmt).unique().one_or_none()

    def upsert_by_slug(self, slug: str, fields: Mapping[str, Any]) -> Wine:
        """Insert or update by slug; always bumps ``modified_at`` on update."""
        payload = dict(fields)
        payload.pop("slug", None)
        existing = self.get_by_slug(slug)
        if existing is None:
            payload["slug"] = slug
            return self.create(payload)
        return self.update(existing.id, payload)  # type: ignore[return-value]

    def get_many_by_ids(self, ids: Sequence[int]) -> list[Wine]:
        """Return wines for ``ids`` in the same order as the input sequence."""
        if not ids:
            return []
        stmt = select(Wine).options(*_WINE_LOAD).where(Wine.id.in_(list(ids)))
        by_id = {w.id: w for w in self._session.scalars(stmt).unique().all()}
        return [by_id[i] for i in ids if i in by_id]

    def search_by_embedding(
        self,
        embedding: Sequence[float],
        *,
        top_k: int = 5,
    ) -> list[RankedHit]:
        """Cosine top-K; no attribute filters in the same SQL (Stage 1)."""
        if top_k <= 0:
            return []
        distance = Wine.embedding.cosine_distance(list(embedding))
        score_expr = (1.0 - distance).label("score")
        stmt = (
            select(Wine, score_expr)
            .options(
                joinedload(Wine.category),
                joinedload(Wine.region),
                joinedload(Wine.sweetness),
            )
            .order_by(distance)
            .limit(top_k)
        )
        rows = self._session.execute(stmt).unique().all()
        hits: list[RankedHit] = []
        for wine, score in rows:
            hits.append(
                RankedHit(
                    wine_id=wine.id,
                    slug=wine.slug,
                    score=float(score),
                    title=wine.title,
                    manufacturer=wine.manufacturer,
                    category=wine.category.name,
                    image_path=wine.image_url,
                )
            )
        return hits

    def search_filters(
        self,
        *,
        category_name: str | None = None,
        sweetness_name: str | None = None,
        region_name: str | None = None,
        manufacturer: str | None = None,
        grape_substring: str | None = None,
        dish: str | None = None,
        rating_min: float | None = None,
        rating_max: float | None = None,
        alcohol_min: float | None = None,
        alcohol_max: float | None = None,
        sort_by_rating: Literal["asc", "desc"] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Wine]:
        """AND attribute filters; no ``title ILIKE``; no vector combo."""
        stmt: Select[tuple[Wine]] = select(Wine).options(*_WINE_LOAD)

        if category_name is not None:
            stmt = stmt.join(Wine.category).where(Category.name == category_name)
        if region_name is not None:
            stmt = stmt.join(Wine.region).where(Region.name == region_name)
        if sweetness_name is not None:
            stmt = stmt.join(Wine.sweetness).where(
                SweetnessLevel.name == sweetness_name
            )
        if manufacturer is not None:
            # Exact match (ILIKE not used in Stage 1).
            stmt = stmt.where(Wine.manufacturer == manufacturer)
        if grape_substring is not None:
            stmt = stmt.where(Wine.grape_variety.ilike(f"%{grape_substring}%"))
        if dish is not None:
            stmt = stmt.where(Wine.dishes.contains([dish]))
        if rating_min is not None:
            stmt = stmt.where(Wine.public_rating >= rating_min)
        if rating_max is not None:
            stmt = stmt.where(Wine.public_rating <= rating_max)
        if alcohol_min is not None:
            stmt = stmt.where(Wine.alcohol_pct >= alcohol_min)
        if alcohol_max is not None:
            stmt = stmt.where(Wine.alcohol_pct <= alcohol_max)

        if sort_by_rating == "asc":
            stmt = stmt.order_by(Wine.public_rating.asc().nulls_last(), Wine.id)
        elif sort_by_rating == "desc":
            stmt = stmt.order_by(Wine.public_rating.desc().nulls_last(), Wine.id)
        else:
            stmt = stmt.order_by(Wine.id)

        stmt = stmt.limit(limit).offset(offset)
        return list(self._session.scalars(stmt).unique().all())

    def _reload(self, wine_id: int) -> Wine | None:
        # Expire so joinedloads re-fetch after flush.
        self._session.expire_all()
        return self.get_by_id(wine_id)
