"""Stage 1.1 — WineRepository CRUD, vector top-K, attribute filters."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.config import load_database_settings
from core.retrieve import encode_image
from db.models import Wine
from db.repository import WineRepository
from db.test_support import (
    DEFAULT_SAMPLE_IMAGE,
    insert_wine_with_embedding,
    unit_embedding,
)

# [TEST-ID] map → tester_1_1_crud.md cases 1–6


def _slug(prefix: str, name: str) -> str:
    return f"{prefix}-{name}"


class TestWineRepositoryCrud:
    """Cases 1–4: create/get/update/delete/batch."""

    def test_create_get_by_id_and_slug(
        self, db_session: Session, slug_prefix: str, track_wine
    ) -> None:
        """[TEST-ID] 1.1-01 create + get_by_id + get_by_slug."""
        repo = WineRepository(db_session)
        emb = unit_embedding(0)
        wine = insert_wine_with_embedding(
            db_session,
            slug=_slug(slug_prefix, "create"),
            title="Test Create Wine",
            embedding=emb,
            category_name="Красное",
            manufacturer="Test Winery",
            image_url=f"/static/wines/{_slug(slug_prefix, 'create')}.webp",
        )
        track_wine(wine.id)
        db_session.flush()

        by_id = repo.get_by_id(wine.id)
        assert by_id is not None
        assert by_id.slug == _slug(slug_prefix, "create")
        assert by_id.title == "Test Create Wine"
        assert by_id.image_url.endswith(".webp")
        assert by_id.embedding is not None
        assert len(by_id.embedding) == len(emb)
        assert by_id.category is not None
        assert by_id.category.name == "Красное"

        by_slug = repo.get_by_slug(_slug(slug_prefix, "create"))
        assert by_slug is not None
        assert by_slug.id == wine.id

    def test_update_moves_modified_at(
        self, db_session: Session, slug_prefix: str, track_wine
    ) -> None:
        """[TEST-ID] 1.1-02 update changes field; modified_at moves forward."""
        repo = WineRepository(db_session)
        wine = insert_wine_with_embedding(
            db_session,
            slug=_slug(slug_prefix, "update"),
            title="Before Update",
            embedding=unit_embedding(1),
        )
        track_wine(wine.id)
        db_session.flush()
        created = repo.get_by_id(wine.id)
        assert created is not None
        before = created.modified_at
        time.sleep(0.05)

        updated = repo.update(wine.id, {"title": "After Update"})
        assert updated is not None
        assert updated.title == "After Update"
        assert updated.modified_at > before

    def test_hard_delete(self, db_session: Session, slug_prefix: str) -> None:
        """[TEST-ID] 1.1-03 hard delete removes row; get returns None."""
        repo = WineRepository(db_session)
        wine = insert_wine_with_embedding(
            db_session,
            slug=_slug(slug_prefix, "delete"),
            title="To Delete",
            embedding=unit_embedding(2),
        )
        wine_id = wine.id
        db_session.flush()

        assert repo.delete(wine_id) is True
        assert repo.get_by_id(wine_id) is None
        assert repo.get_by_slug(_slug(slug_prefix, "delete")) is None
        # Already gone — fixture cleanup is a no-op for this id.
        assert repo.delete(wine_id) is False

    def test_get_many_by_ids(
        self, db_session: Session, slug_prefix: str, track_wine
    ) -> None:
        """[TEST-ID] 1.1-04 get_many_by_ids returns requested ids (input order)."""
        repo = WineRepository(db_session)
        w1 = insert_wine_with_embedding(
            db_session,
            slug=_slug(slug_prefix, "many-a"),
            title="Many A",
            embedding=unit_embedding(3),
        )
        w2 = insert_wine_with_embedding(
            db_session,
            slug=_slug(slug_prefix, "many-b"),
            title="Many B",
            embedding=unit_embedding(4),
        )
        track_wine(w1.id)
        track_wine(w2.id)
        db_session.flush()

        ordered = repo.get_many_by_ids([w2.id, w1.id, 9_999_999_999])
        assert [w.id for w in ordered] == [w2.id, w1.id]


class TestWineRepositorySearch:
    """Cases 5–6: vector top-K and attribute filters."""

    def test_search_by_embedding_rank1(
        self, db_session: Session, slug_prefix: str, track_wine
    ) -> None:
        """[TEST-ID] 1.1-05 search_by_embedding; real DINO query ranks target first."""
        sample = Path(DEFAULT_SAMPLE_IMAGE)
        if not sample.is_file():
            pytest.fail(f"sample image missing for DINO path: {sample}")

        target_emb = encode_image(str(sample))
        assert len(target_emb) == load_database_settings().embedding_dim

        repo = WineRepository(db_session)
        target = insert_wine_with_embedding(
            db_session,
            slug=_slug(slug_prefix, "vec-target"),
            title="DINO Target",
            embedding=target_emb,
            category_name="Розовое",
            manufacturer="Massandra",
        )
        decoy_a = insert_wine_with_embedding(
            db_session,
            slug=_slug(slug_prefix, "vec-decoy-a"),
            title="Decoy A",
            embedding=unit_embedding(10),
        )
        decoy_b = insert_wine_with_embedding(
            db_session,
            slug=_slug(slug_prefix, "vec-decoy-b"),
            title="Decoy B",
            embedding=unit_embedding(20),
        )
        for w in (target, decoy_a, decoy_b):
            track_wine(w.id)
        db_session.flush()

        hits = repo.search_by_embedding(target_emb, top_k=5)
        assert len(hits) >= 1
        assert hits[0]["slug"] == target.slug
        assert hits[0]["wine_id"] == target.id
        assert hits[0]["score"] > hits[-1]["score"] or len(hits) == 1
        assert "title" in hits[0]
        assert "manufacturer" in hits[0]
        assert "category" in hits[0]
        assert "image_path" in hits[0]
        # Target should outrank orthogonal decoys among our three.
        our_slugs = {target.slug, decoy_a.slug, decoy_b.slug}
        our_hits = [h for h in hits if h["slug"] in our_slugs]
        assert our_hits[0]["slug"] == target.slug

    def test_search_filters(
        self, db_session: Session, slug_prefix: str, track_wine
    ) -> None:
        """[TEST-ID] 1.1-06 category_name, rating_min, dish overlap, sort_by_rating."""
        repo = WineRepository(db_session)

        red_high = insert_wine_with_embedding(
            db_session,
            slug=_slug(slug_prefix, "flt-red-high"),
            title="Red High",
            embedding=unit_embedding(30),
            category_name="Красное",
            extra={
                "public_rating": 4.8,
                "dishes": ["стейк", "сыр"],
            },
        )
        red_low = insert_wine_with_embedding(
            db_session,
            slug=_slug(slug_prefix, "flt-red-low"),
            title="Red Low",
            embedding=unit_embedding(31),
            category_name="Красное",
            extra={
                "public_rating": 3.2,
                "dishes": ["рыба"],
            },
        )
        white = insert_wine_with_embedding(
            db_session,
            slug=_slug(slug_prefix, "flt-white"),
            title="White Mid",
            embedding=unit_embedding(32),
            category_name="Белое",
            extra={
                "public_rating": 4.5,
                "dishes": ["стейк"],
            },
        )
        for w in (red_high, red_low, white):
            track_wine(w.id)
        db_session.flush()
        # Limit = whole catalog so test rows are never cut off by real wines.
        everything = db_session.scalar(select(func.count()).select_from(Wine))
        assert everything

        by_cat = repo.search_filters(category_name="Красное", limit=everything)
        cat_slugs = {w.slug for w in by_cat}
        assert red_high.slug in cat_slugs
        assert red_low.slug in cat_slugs
        assert white.slug not in cat_slugs

        by_rating = repo.search_filters(rating_min=4.0, limit=everything)
        rating_slugs = {w.slug for w in by_rating}
        assert red_high.slug in rating_slugs
        assert white.slug in rating_slugs
        assert red_low.slug not in rating_slugs

        by_dish = repo.search_filters(dish="стейк", limit=everything)
        dish_slugs = {w.slug for w in by_dish}
        assert red_high.slug in dish_slugs
        assert white.slug in dish_slugs
        assert red_low.slug not in dish_slugs

        sorted_desc = repo.search_filters(
            category_name="Красное",
            sort_by_rating="desc",
            limit=everything,
        )
        our_desc = [w for w in sorted_desc if w.slug.startswith(slug_prefix)]
        assert len(our_desc) >= 2
        assert our_desc[0].slug == red_high.slug
        assert our_desc[1].slug == red_low.slug

        sorted_asc = repo.search_filters(
            category_name="Красное",
            sort_by_rating="asc",
            limit=everything,
        )
        our_asc = [w for w in sorted_asc if w.slug.startswith(slug_prefix)]
        assert our_asc[0].slug == red_low.slug
        assert our_asc[1].slug == red_high.slug
