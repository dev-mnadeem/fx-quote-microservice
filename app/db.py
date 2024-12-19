"""Engine, session factory and declarative base.

The engine is created lazily so that importing the package does not open a
database handle -- tests replace the session dependency instead.
"""

from __future__ import annotations

from collections.abc import Generator, Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Column, DateTime, Engine, Integer, create_engine, func
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import get_settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    settings = get_settings()
    kwargs: dict[str, object] = {'future': True}
    if settings.is_sqlite:
        # FastAPI serves requests from a threadpool, so the connection may be
        # touched by a thread other than the one that created it.
        kwargs['connect_args'] = {'check_same_thread': False}
    return create_engine(settings.database_url, **kwargs)


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(
        bind=get_engine(),
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


class TimestampedModel:
    """Surrogate key plus audit columns shared by every table."""

    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )


Base = declarative_base(cls=TimestampedModel)


def create_schema() -> None:
    """Create any missing tables. Safe to call repeatedly."""

    import app.models  # noqa: F401  (registers the mappers)

    Base.metadata.create_all(bind=get_engine())


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a request-scoped session."""

    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Session for code outside the request cycle (CLI, scheduler).

    Unlike a bare ``next(get_session())`` this always closes the session and
    rolls back on failure.
    """

    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
