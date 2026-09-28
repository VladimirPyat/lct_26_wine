"""Shared fixtures for Stage 1 wine repository / catalog-load tests."""

from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest
from sqlalchemy.orm import Session

from db.repository import WineRepository
from db.session import create_db_engine, create_session_factory


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "catalog_load: Stage 1.2 prepare CSV + imported DB checks"
    )
    config.addinivalue_line(
        "markers", "import_check: Stage 1.2 post-import SQL / repository smoke"
    )
    config.addinivalue_line(
        "markers", "integration: optional live external services (skip without key)"
    )
    config.addinivalue_line(
        "markers", "e2e: live API / owner_eval harness (needs running uvicorn)"
    )
    config.addinivalue_line(
        "markers", "db: read-only checks against Compose Postgres (skip if down)"
    )


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Real Postgres session; hard-delete wines tagged with the slug prefix."""
    engine = create_db_engine()
    factory = create_session_factory(engine)
    session = factory()
    prefix = f"t11-{uuid.uuid4().hex[:12]}"
    session.info["test_slug_prefix"] = prefix
    session.info["created_wine_ids"] = []
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        ids: list[int] = list(session.info.get("created_wine_ids", []))
        repo = WineRepository(session)
        for wine_id in ids:
            repo.delete(wine_id)
        try:
            session.commit()
        except Exception:
            session.rollback()
        session.close()


@pytest.fixture
def slug_prefix(db_session: Session) -> str:
    return str(db_session.info["test_slug_prefix"])


@pytest.fixture
def track_wine(db_session: Session):
    """Record wine ids for fixture cleanup (hard delete)."""

    def _track(wine_id: int) -> None:
        ids: list[int] = db_session.info.setdefault("created_wine_ids", [])
        ids.append(wine_id)

    return _track
