"""Database engine and session management."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session, sessionmaker

from ..config import get_database_url
from .models import Base

_engine = None
_SessionLocal: Optional[sessionmaker] = None


def _get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        url = get_database_url()
        connect_args = {}
        if url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        _engine = create_engine(
            url,
            pool_pre_ping=not url.startswith("sqlite"),
            connect_args=connect_args,
        )
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine


def is_store_available() -> bool:
    """Return True if the database is reachable."""
    try:
        engine = _get_engine()
        with engine.connect():
            return True
    except Exception:
        return False


def init_db() -> None:
    """Create all tables (development / first-run helper)."""
    Base.metadata.create_all(bind=_get_engine())


def tables_exist() -> bool:
    try:
        inspector = inspect(_get_engine())
        return "jobs" in inspector.get_table_names()
    except Exception:
        return False


def reset_db_engine() -> None:
    """Reset engine (for tests)."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context manager yielding a SQLAlchemy session."""
    if _SessionLocal is None:
        _get_engine()
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
