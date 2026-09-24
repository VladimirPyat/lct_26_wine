"""Initial catalog schema: lookups, wines + pgvector, sweetness seed.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-24 01:30:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

from core.config import load_database_settings

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SWEETNESS_SEED = (
    "сухое",
    "полусухое",
    "полусладкое",
    "сладкое",
    "брют",
    "экстра брют",
)


def upgrade() -> None:
    """Create extension, tables, and seed sweetness_levels."""
    embedding_dim = load_database_settings().embedding_dim
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))

    op.create_table(
        "categories",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "regions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "sweetness_levels",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "wines",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("category_id", sa.BigInteger(), nullable=False),
        sa.Column("color", sa.Text(), nullable=False),
        sa.Column("region_id", sa.BigInteger(), nullable=False),
        sa.Column("grape_variety", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("manufacturer", sa.Text(), nullable=False),
        sa.Column("public_rating", sa.Double(), nullable=True),
        sa.Column("product_url", sa.Text(), nullable=True),
        sa.Column("serving_temperature", sa.Text(), nullable=True),
        sa.Column("alcohol_pct", sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column("dishes", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("sweetness_id", sa.BigInteger(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(embedding_dim), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "modified_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["region_id"], ["regions.id"]),
        sa.ForeignKeyConstraint(["sweetness_id"], ["sweetness_levels.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    sweetness = sa.table(
        "sweetness_levels",
        sa.column("name", sa.Text()),
    )
    op.bulk_insert(
        sweetness,
        [{"name": name} for name in _SWEETNESS_SEED],
    )


def downgrade() -> None:
    """Drop catalog tables (extension left installed)."""
    op.drop_table("wines")
    op.drop_table("sweetness_levels")
    op.drop_table("regions")
    op.drop_table("categories")
