"""Rate and conversion services."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.providers.base import RateSnapshot
from app.services import (
    ConversionService,
    NoRatesAvailableError,
    RateService,
    UnknownCurrencyError,
    ingest_snapshot,
)
from app.services.rates import normalise_code, normalise_codes
from tests.conftest import TODAY, YESTERDAY


def test_latest_means_newest_published_not_today(session: Session) -> None:
    """The ECB does not publish at weekends, so "today" is the wrong key."""

    stale = date(2020, 6, 1)
    ingest_snapshot(session, RateSnapshot(rate_date=stale, rates={'USD': 1.1}))

    page = RateService(session).list_latest(limit=10, offset=0)

    assert page.rate_date == stale
    assert len(page.items) == 1


def test_an_empty_database_says_so_rather_than_returning_nothing(
    session: Session,
) -> None:
    with pytest.raises(NoRatesAvailableError):
        RateService(session).list_latest(limit=10, offset=0)


def test_has_more_is_true_while_rows_remain(
    two_snapshots: Session,
) -> None:
    page = RateService(two_snapshots).list_latest(limit=2, offset=0)

    assert page.total == 4
    assert page.has_more is True


def test_has_more_is_false_on_the_final_page(
    two_snapshots: Session,
) -> None:
    page = RateService(two_snapshots).list_latest(limit=2, offset=2)

    assert page.has_more is False


def test_currency_filters_are_case_insensitive(
    two_snapshots: Session,
) -> None:
    page = RateService(two_snapshots).list_latest(
        limit=10, offset=0, currencies=['usd', ' jpy ']
    )

    assert {row.currency for row in page.items} == {'USD', 'JPY'}


def test_a_currency_missing_from_the_latest_day_is_a_known_error(
    two_snapshots: Session,
) -> None:
    with pytest.raises(UnknownCurrencyError) as caught:
        RateService(two_snapshots).get_latest_quote('chf')

    assert caught.value.currency == 'CHF'


def test_history_spans_publication_dates(two_snapshots: Session) -> None:
    rows = RateService(two_snapshots).history('usd', limit=10)

    assert [row.rate_date for row in rows] == [TODAY, YESTERDAY]


def test_history_for_an_unseen_currency_raises(
    two_snapshots: Session,
) -> None:
    with pytest.raises(UnknownCurrencyError):
        RateService(two_snapshots).history('XYZ', limit=10)


def test_known_currencies_always_include_the_base(
    two_snapshots: Session,
) -> None:
    codes = RateService(two_snapshots).known_currencies()

    assert 'EUR' in codes
    assert 'USD' in codes


def test_normalise_code_trims_and_upper_cases() -> None:
    assert normalise_code('  usd ') == 'USD'


def test_normalise_codes_drops_blanks_and_duplicates() -> None:
    assert normalise_codes(['usd', 'USD', '', '  ', 'jpy']) == ['USD', 'JPY']


def test_converting_from_the_base_currency_uses_the_stored_rate(
    two_snapshots: Session,
) -> None:
    result = ConversionService(two_snapshots).convert('EUR', 'USD', 100)

    assert result.rate == pytest.approx(1.05)
    assert result.converted == pytest.approx(105.0)


def test_converting_into_the_base_currency_inverts_the_rate(
    two_snapshots: Session,
) -> None:
    result = ConversionService(two_snapshots).convert('USD', 'EUR', 105)

    assert result.converted == pytest.approx(100.0, abs=1e-4)


def test_a_cross_rate_goes_through_the_euro(
    two_snapshots: Session,
) -> None:
    result = ConversionService(two_snapshots).convert('USD', 'JPY', 1)

    assert result.rate == pytest.approx(164.0 / 1.05, abs=1e-8)
    assert result.base == 'EUR'


def test_converting_a_currency_to_itself_is_the_identity(
    two_snapshots: Session,
) -> None:
    result = ConversionService(two_snapshots).convert('JPY', 'JPY', 42)

    assert result.rate == pytest.approx(1.0)
    assert result.converted == pytest.approx(42.0)


def test_conversion_is_dated_by_the_snapshot_it_used(
    two_snapshots: Session,
) -> None:
    assert (
        ConversionService(two_snapshots).convert('USD', 'GBP', 1).rate_date
        == TODAY
    )


@pytest.mark.parametrize(
    ('source', 'target'), [('XYZ', 'USD'), ('USD', 'XYZ')]
)
def test_an_unknown_currency_on_either_side_raises(
    two_snapshots: Session, source: str, target: str
) -> None:
    with pytest.raises(UnknownCurrencyError):
        ConversionService(two_snapshots).convert(source, target, 1)


def test_conversion_on_an_empty_database_raises(session: Session) -> None:
    with pytest.raises(NoRatesAvailableError):
        ConversionService(session).convert('USD', 'EUR', 1)
