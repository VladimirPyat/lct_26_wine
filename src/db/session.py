"""SQLAlchemy engine / session helpers (DATABASE_URL from env / .env)."""

from __future__ import annotations

import os
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from core.env import load_dotenv


def get_database_url() -> str:
    """Resolve ``DATABASE_URL`` (host app → Compose Postgres). Never log the value."""
    load_dotenv()
    url = os.environ.get("DATABASE_URL")
    if not url:
        msg = (
            "DATABASE_URL is not set. Copy .env.example to .env "
            "or export DATABASE_URL for the host Postgres."
        )
        raise RuntimeError(msg)
    return url


def create_db_engine(*, echo: bool = False) -> Engine:
    """Create a SQLAlchemy engine for the catalog database."""
    return create_engine(get_database_url(), echo=echo, pool_pre_ping=True)


def create_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    """Return a ``sessionmaker`` bound to ``engine`` (or a new default engine)."""
    eng = engine if engine is not None else create_db_engine()
    return sessionmaker(bind=eng, expire_on_commit=False, class_=Session)


@contextmanager
def session_scope(
    factory: sessionmaker[Session] | None = None,
) -> Generator[Session, None, None]:
    """Commit on success, rollback on error; always close the session."""
    session_factory = factory if factory is not None else create_session_factory()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
