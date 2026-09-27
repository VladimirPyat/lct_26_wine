"""Stage 1.2 — catalog prepare artifacts + imported DB smoke verification.

Does not re-run full import. Reads Compose DB and prepare CSVs as left by @Coder.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.config import load_database_settings
from core.retrieve import encode_image
from db.repository import WineRepository

ROOT = Path(__file__).resolve().parents[1]
PREPARE = ROOT / "scripts" / "catalog_prepare"
STATIC = ROOT / "static" / "wines"

SHARED_COLS = {
    "slug",
    "title",
    "category",
    "color",
    "region",
    "grape_variety",
    "description",
    "manufacturer",
    "source_image",
    "product_url",
    "image_source",
}
ENRICH_COLS = {
    "public_rating",
    "serving_temperature",
    "alcohol_pct",
    "dishes",
}

EXPECTED_READY = 1932
EXPECTED_ADDITIONAL = 18
EXPECTED_REJECTED = 153
EXPECTED_IMPORTED = EXPECTED_READY + EXPECTED_ADDITIONAL
SWEETNESS_CANONICAL = {
    "сухое",
    "полусухое",
    "полусладкое",
    "сладкое",
    "брют",
    "экстра брют",
}


def _read_csv(name: str) -> list[dict[str, str]]:
    path = PREPARE / name
    assert path.is_file(), f"missing prepare artifact: {path}"
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


@pytest.mark.catalog_load
class TestCatalogPrepareFiles:
    """File-level checks for prepare outputs."""

    def test_ready_csv_count_and_enrich(self) -> None:
        """[TEST-ID] 1.2-01 wines_ready.csv non-empty with enrich columns."""
        rows = _read_csv("wines_ready.csv")
        assert len(rows) == EXPECTED_READY
        cols = set(rows[0].keys())
        assert SHARED_COLS <= cols
        assert ENRICH_COLS <= cols
        assert "reason" not in cols

    def test_additional_csv_count_and_enrich(self) -> None:
        """[TEST-ID] 1.2-02 wines_additional.csv ~15 rows with enrich."""
        rows = _read_csv("wines_additional.csv")
        assert len(rows) == EXPECTED_ADDITIONAL
        cols = set(rows[0].keys())
        assert SHARED_COLS <= cols
        assert ENRICH_COLS <= cols

    def test_rejected_csv_has_reason(self) -> None:
        """[TEST-ID] 1.2-03 wines_rejected.csv has reason; enrich present."""
        rows = _read_csv("wines_rejected.csv")
        assert len(rows) == EXPECTED_REJECTED
        cols = set(rows[0].keys())
        assert SHARED_COLS <= cols
        assert ENRICH_COLS <= cols
        assert "reason" in cols
        empty = [r["slug"] for r in rows if not (r.get("reason") or "").strip()]
        assert empty == []


@pytest.mark.catalog_load
@pytest.mark.import_check
class TestCatalogImportDb:
    """SQL + repository smoke against the already-imported catalog."""

    def test_lookup_tables_and_wine_counts(self, db_session: Session) -> None:
        """[TEST-ID] 1.2-04 tables exist; sweetness ≥6;
        wines≈ready+additional; no nulls."""
        present = {
            r[0]
            for r in db_session.execute(
                text(
                    """
                    SELECT tablename FROM pg_tables
                    WHERE schemaname = 'public'
                      AND tablename IN (
                        'categories', 'regions', 'sweetness_levels', 'wines'
                      )
                    """
                )
            )
        }
        assert present == {
            "categories",
            "regions",
            "sweetness_levels",
            "wines",
        }

        sweet_count, sweet_names = db_session.execute(
            text("SELECT count(*), array_agg(name ORDER BY name) FROM sweetness_levels")
        ).one()
        assert sweet_count >= 6
        assert SWEETNESS_CANONICAL <= set(sweet_names)

        n, emb_null, img_empty = db_session.execute(
            text(
                """
                SELECT
                  count(*) AS n,
                  count(*) FILTER (WHERE embedding IS NULL) AS emb_null,
                  count(*) FILTER (
                    WHERE image_url IS NULL OR image_url = ''
                  ) AS img_empty
                FROM wines
                """
            )
        ).one()
        assert n == EXPECTED_IMPORTED
        assert emb_null == 0
        assert img_empty == 0

    def test_ready_static_file_spot_check(self) -> None:
        """[TEST-ID] 1.2-05 ready slug has file under static/wines/."""
        ready = _read_csv("wines_ready.csv")
        slug = ready[0]["slug"]
        path = STATIC / f"{slug}.webp"
        assert path.is_file(), f"missing static image for {slug}: {path}"
        assert path.stat().st_size > 0

    def test_get_by_slug_ready_and_additional(self, db_session: Session) -> None:
        """[TEST-ID] 1.2-06 get_by_slug for one ready and one additional."""
        ready_slug = _read_csv("wines_ready.csv")[0]["slug"]
        add_slug = _read_csv("wines_additional.csv")[0]["slug"]
        repo = WineRepository(db_session)

        ready = repo.get_by_slug(ready_slug)
        assert ready is not None
        assert ready.slug == ready_slug
        assert ready.embedding is not None
        assert ready.image_url
        assert ready.image_url.endswith(".webp")

        additional = repo.get_by_slug(add_slug)
        assert additional is not None
        assert additional.slug == add_slug
        assert additional.embedding is not None
        assert additional.image_url

    def test_search_by_embedding_smoke_imported_image(
        self, db_session: Session
    ) -> None:
        """[TEST-ID] 1.2-07 encode imported image → slug in top_k=5."""
        ready_slug = _read_csv("wines_ready.csv")[0]["slug"]
        image = STATIC / f"{ready_slug}.webp"
        assert image.is_file()

        emb = encode_image(str(image))
        assert len(emb) == load_database_settings().embedding_dim

        repo = WineRepository(db_session)
        hits = repo.search_by_embedding(emb, top_k=5)
        assert len(hits) >= 1
        hit_slugs = [h["slug"] for h in hits]
        assert ready_slug in hit_slugs, (
            f"expected {ready_slug} in top 5, got {hit_slugs}"
        )
