"""Ingest computes day-over-day moves and stays idempotent."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ExchangeRate
from app.providers.base import RateSnapshot
from app.services import compute_changes, ingest_snapshot
from tests.conftest import LATEST_RATES, PREVIOUS_RATES, TODAY, YESTERDAY


def test_change_is_none_when_a_currency_is_seen_for_the_first_time() -> None:
    changes = compute_changes({'USD': 1.05}, previous={})

    assert changes == {'USD': None}


def test_change_is_the_absolute_move_against_the_previous_day() -> None:
    changes = compute_changes({'USD': 1.05}, previous={'USD': 1.04})

    assert changes['USD'] == pytest.approx(0.01, abs=1e-9)


def test_first_ingest_stores_every_quote(session: Session) -> None:
    result = ingest_snapshot(
        session, RateSnapshot(rate_date=YESTERDAY, rates=PREVIOUS_RATES)
    )

    assert result.inserted == len(PREVIOUS_RATES)
    assert result.updated == 0
    assert result.compared_against is None


def test_second_day_is_compared_against_the_first(session: Session) -> None:
    ingest_snapshot(
        session, RateSnapshot(rate_date=YESTERDAY, rates=PREVIOUS_RATES)
    )

    result = ingest_snapshot(
        session, RateSnapshot(rate_date=TODAY, rates=LATEST_RATES)
    )

    assert result.compared_against == YESTERDAY
    assert result.inserted == len(LATEST_RATES)


def test_a_currency_new_on_the_second_day_has_no_change(
    two_snapshots: Session,
) -> None:
    row = two_snapshots.execute(
        select(ExchangeRate).where(
            ExchangeRate.currency == 'SEK',
            ExchangeRate.rate_date == TODAY,
        )
    ).scalar_one()

    assert row.change is None


def test_a_falling_currency_records_a_negative_change(
    two_snapshots: Session,
) -> None:
    row = two_snapshots.execute(
        select(ExchangeRate).where(
            ExchangeRate.currency == 'GBP',
            ExchangeRate.rate_date == TODAY,
        )
    ).scalar_one()

    assert row.change < 0


def test_re_running_the_same_day_updates_instead_of_duplicating(
    session: Session,
) -> None:
    snapshot = RateSnapshot(rate_date=TODAY, rates=LATEST_RATES)
    ingest_snapshot(session, snapshot)

    second = ingest_snapshot(session, snapshot)

    assert second.inserted == 0
    assert second.updated == len(LATEST_RATES)
    total = session.execute(
        select(func.count()).select_from(ExchangeRate)
    ).scalar_one()
    assert total == len(LATEST_RATES)


def test_a_corrected_rate_overwrites_the_stored_one(
    session: Session,
) -> None:
    ingest_snapshot(session, RateSnapshot(rate_date=TODAY, rates={'USD': 1.0}))

    ingest_snapshot(session, RateSnapshot(rate_date=TODAY, rates={'USD': 9.0}))

    row = session.execute(
        select(ExchangeRate).where(ExchangeRate.currency == 'USD')
    ).scalar_one()
    assert row.rate == 9.0


def test_an_older_snapshot_can_be_backfilled(session: Session) -> None:
    ingest_snapshot(session, RateSnapshot(rate_date=TODAY, rates=LATEST_RATES))

    result = ingest_snapshot(
        session,
        RateSnapshot(rate_date=date(2026, 1, 2), rates=PREVIOUS_RATES),
    )

    assert result.compared_against is None
