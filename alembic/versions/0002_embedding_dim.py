"""Align wines.embedding vector dim with config/database.yaml embedding_dim.

Revision ID: 0002_embedding_dim
Revises: 0001_initial_schema
Create Date: 2026-09-27 23:00:00
"""

from __future__ import annotations

import os
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from core.config import load_database_settings

# revision identifiers, used by Alembic.
revision: str = "0002_embedding_dim"
down_revision: Union[str, Sequence[str], None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_RESET_ENV = "VINE_RESET_EMBEDDINGS"


def upgrade() -> None:
    """Retype ``wines.embedding`` to ``vector(<config dim>)``.

    Embeddings of another dim cannot be converted: a non-empty table is only
    wiped when ``VINE_RESET_EMBEDDINGS=1``; otherwise the migration refuses.
    """
    target = load_database_settings().embedding_dim
    bind = op.get_bind()
    # pgvector stores the declared dim in atttypmod.
    current = bind.execute(
        sa.text(
            "SELECT atttypmod FROM pg_attribute "
            "WHERE attrelid = 'wines'::regclass AND attname = 'embedding'"
        )
    ).scalar_one()
    if int(current) == target:
        return

    rows = int(bind.execute(sa.text("SELECT count(*) FROM wines")).scalar_one())
    if rows > 0:
        if os.environ.get(_RESET_ENV) != "1":
            msg = (
                f"wines.embedding is vector({current}) with {rows} rows, config "
                f"embedding_dim={target}. Embeddings of another dim cannot be "
                f"converted: rerun with {_RESET_ENV}=1 (deletes all wines rows), "
                "then reimport the catalog."
            )
            raise RuntimeError(msg)
        op.execute(sa.text("DELETE FROM wines"))

    op.execute(
        sa.text(f"ALTER TABLE wines ALTER COLUMN embedding TYPE vector({int(target)})")
    )


def downgrade() -> None:
    """No-op: dim is config-driven.

    To go back, restore the previous ``embedding_dim`` in ``database.yaml`` and
    rerun the upgrade logic (``alembic downgrade 0001 && alembic upgrade head``
    with ``VINE_RESET_EMBEDDINGS=1``), then reimport. Data is never dropped here.
    """
