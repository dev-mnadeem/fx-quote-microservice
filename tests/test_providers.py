"""Provider parsing, error handling and the registry."""

from __future__ import annotations

from datetime import date

import pytest

from app.config import Settings
from app.providers import (
    EcbRateProvider,
    RateProvider,
    RateProviderError,
    RateSnapshot,
    StaticRateProvider,
    available_providers,
    build_provider,
    parse_ecb_document,
)

ECB_DOCUMENT = b"""<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope
    xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01"
    xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
  <Cube>
    <Cube time="2026-03-13">
      <Cube currency="USD" rate="1.0500"/>
      <Cube currency="JPY" rate="164.00"/>
      <Cube currency="gbp" rate="0.8250"/>
    </Cube>
  </Cube>
</gesmes:Envelope>
"""


def test_parses_the_publication_date_rather_than_assuming_today() -> None:
    snapshot = parse_ecb_document(ECB_DOCUMENT)

    assert snapshot.rate_date == date(2026, 3, 13)


def test_parses_every_quote_and_upper_cases_the_code() -> None:
    snapshot = parse_ecb_document(ECB_DOCUMENT)

    assert snapshot.rates == {'USD': 1.05, 'JPY': 164.0, 'GBP': 0.825}
    assert snapshot.currencies == ['GBP', 'JPY', 'USD']


def test_the_base_currency_is_euro() -> None:
    assert parse_ecb_document(ECB_DOCUMENT).base == 'EUR'


def test_malformed_xml_raises_a_provider_error() -> None:
    with pytest.raises(RateProviderError, match='malformed'):
        parse_ecb_document(b'<Envelope><Cube')


def test_a_document_with_no_dated_cube_raises() -> None:
    with pytest.raises(RateProviderError, match='no dated cube'):
        parse_ecb_document(b'<Envelope><Cube/></Envelope>')


def test_a_document_with_an_unparseable_date_raises() -> None:
    payload = b'<Envelope><Cube><Cube time="not-a-date"/></Cube></Envelope>'

    with pytest.raises(RateProviderError, match='unparseable date'):
        parse_ecb_document(payload)


def test_a_document_with_no_quotes_raises() -> None:
    payload = b'<Envelope><Cube><Cube time="2026-03-13"/></Cube></Envelope>'

    with pytest.raises(RateProviderError, match='no quotes'):
        parse_ecb_document(payload)


def test_a_non_numeric_rate_raises() -> None:
    payload = (
        b'<Envelope><Cube><Cube time="2026-03-13">'
        b'<Cube currency="USD" rate="n/a"/>'
        b'</Cube></Cube></Envelope>'
    )

    with pytest.raises(RateProviderError, match='unusable rate for USD'):
        parse_ecb_document(payload)


def test_a_snapshot_must_not_be_empty() -> None:
    with pytest.raises(ValueError, match='at least one rate'):
        RateSnapshot(rate_date=date(2026, 3, 13), rates={})


def test_a_snapshot_must_not_quote_its_own_base() -> None:
    with pytest.raises(ValueError, match='must not appear'):
        RateSnapshot(rate_date=date(2026, 3, 13), rates={'EUR': 1.0})


def test_the_static_provider_needs_no_network() -> None:
    snapshot = StaticRateProvider().fetch_latest()

    assert snapshot.rate_date == date.today()
    assert 'USD' in snapshot.rates


def test_the_static_provider_accepts_a_fixed_date_and_rates() -> None:
    provider = StaticRateProvider(
        rates={'USD': 2.0}, rate_date=date(2020, 1, 1)
    )

    snapshot = provider.fetch_latest()

    assert snapshot.rate_date == date(2020, 1, 1)
    assert snapshot.rates == {'USD': 2.0}


def test_registry_lists_both_providers() -> None:
    assert available_providers() == ['ecb', 'static']


@pytest.mark.parametrize(
    ('name', 'expected'),
    [('ecb', EcbRateProvider), ('static', StaticRateProvider)],
)
def test_build_provider_returns_the_named_provider(
    name: str, expected: type
) -> None:
    provider = build_provider(Settings(rates_provider=name))

    assert isinstance(provider, expected)
    assert isinstance(provider, RateProvider)


def test_build_provider_names_the_valid_options_when_asked_for_junk() -> None:
    with pytest.raises(ValueError, match='ecb, static'):
        build_provider(Settings(rates_provider='yahoo'))
