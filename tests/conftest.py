"""Shared fixtures.

Every test runs against a throwaway SQLite file configured entirely
through the environment, so the production defaults are never touched and
no test needs network access.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import create_schema, get_engine, get_session_factory
from app.main import create_app
from app.models import ExchangeRate
from app.providers.base import RateSnapshot
from app.services import ingest_snapshot

TODAY = date(2026, 3, 13)
YESTERDAY = TODAY - timedelta(days=1)

# A small, fixed snapshot pair: enough currencies to exercise paging and
# cross rates, small enough to assert on by hand.
PREVIOUS_RATES = {'USD': 1.0400, 'GBP': 0.8300, 'JPY': 162.00, 'CHF': 0.9400}
LATEST_RATES = {'USD': 1.0500, 'GBP': 0.8250, 'JPY': 164.00, 'SEK': 11.5000}


def _reset_caches() -> None:
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()


@pytest.fixture(scope='session', autouse=True)
def _environment(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    database = tmp_path_factory.mktemp('data') / 'test.db'
    os.environ.update(
        {
            'DATABASE_URL': f'sqlite:///{database}',
            'RATES_PROVIDER': 'static',
            'NLQ_PROVIDER': 'rules',
            'SCHEDULER_ENABLED': 'false',
            'DEFAULT_PAGE_SIZE': '50',
            'MAX_PAGE_SIZE': '200',
        }
    )
    os.environ.pop('ANTHROPIC_API_KEY', None)
    _reset_caches()
    create_schema()
    yield
    _reset_caches()


@pytest.fixture
def session() -> Iterator[Session]:
    """An empty database and a session onto it."""

    factory = get_session_factory()
    with factory() as cleaner:
        cleaner.execute(delete(ExchangeRate))
        cleaner.commit()

    db = factory()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def two_snapshots(session: Session) -> Session:
    """Two consecutive publication dates, so ``change`` is populated."""

    ingest_snapshot(
        session, RateSnapshot(rate_date=YESTERDAY, rates=PREVIOUS_RATES)
    )
    ingest_snapshot(session, RateSnapshot(rate_date=TODAY, rates=LATEST_RATES))
    return session


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    """A client against an app whose database starts empty."""

    with TestClient(create_app(get_settings())) as test_client:
        yield test_client


@pytest.fixture
def seeded_client(two_snapshots: Session) -> Iterator[TestClient]:
    """A client against an app holding both snapshots."""

    with TestClient(create_app(get_settings())) as test_client:
        yield test_client
