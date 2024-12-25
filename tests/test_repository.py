"""The data-access layer answers snapshot questions in one query each."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories import ExchangeRateRepository
from tests.conftest import LATEST_RATES, TODAY, YESTERDAY


def test_latest_rate_date_is_none_on_an_empty_database(
    session: Session,
) -> None:
    assert ExchangeRateRepository(session).latest_rate_date() is None


def test_latest_rate_date_is_the_newest_publication(
    two_snapshots: Session,
) -> None:
    assert ExchangeRateRepository(two_snapshots).latest_rate_date() == TODAY


def test_previous_rate_date_skips_the_current_day(
    two_snapshots: Session,
) -> None:
    repository = ExchangeRateRepository(two_snapshots)

    assert repository.previous_rate_date(TODAY) == YESTERDAY


def test_snapshot_rates_returns_a_plain_dict(
    two_snapshots: Session,
) -> None:
    rates = ExchangeRateRepository(two_snapshots).snapshot_rates(TODAY)

    assert rates == LATEST_RATES


def test_paging_is_ordered_by_currency(two_snapshots: Session) -> None:
    repository = ExchangeRateRepository(two_snapshots)

    first = repository.page_for_date(TODAY, limit=2, offset=0)
    second = repository.page_for_date(TODAY, limit=2, offset=2)

    assert [row.currency for row in first] == ['GBP', 'JPY']
    assert [row.currency for row in second] == ['SEK', 'USD']


def test_filtering_narrows_both_the_page_and_the_count(
    two_snapshots: Session,
) -> None:
    repository = ExchangeRateRepository(two_snapshots)

    rows = repository.page_for_date(
        TODAY, limit=10, offset=0, currencies=['USD', 'JPY']
    )

    assert {row.currency for row in rows} == {'USD', 'JPY'}
    assert repository.count_for_date(TODAY, ['USD', 'JPY']) == 2


def test_history_is_newest_first(two_snapshots: Session) -> None:
    rows = ExchangeRateRepository(two_snapshots).history('USD', limit=10)

    assert [row.rate_date for row in rows] == [TODAY, YESTERDAY]


def test_history_respects_its_limit(two_snapshots: Session) -> None:
    rows = ExchangeRateRepository(two_snapshots).history('USD', limit=1)

    assert len(rows) == 1


def test_distinct_currencies_spans_every_snapshot(
    two_snapshots: Session,
) -> None:
    codes = ExchangeRateRepository(two_snapshots).distinct_currencies()

    assert codes == ['CHF', 'GBP', 'JPY', 'SEK', 'USD']


def test_get_quote_returns_none_for_a_currency_absent_that_day(
    two_snapshots: Session,
) -> None:
    repository = ExchangeRateRepository(two_snapshots)

    assert repository.get_quote('CHF', TODAY) is None
    assert repository.get_quote('CHF', YESTERDAY) is not None
