"""A fixed snapshot, so the service runs with no network access.

Used by the test suite, by ``RATES_PROVIDER=static``, and by anyone who
wants to try the API on a train. The numbers are a plausible frozen sample,
not a live quote -- ``fetch_latest`` dates them to today so the ordinary
"latest snapshot" query has something to return.
"""

from __future__ import annotations

from datetime import date

from app.providers.base import RateSnapshot

# Units of each currency bought by one euro.
SAMPLE_RATES: dict[str, float] = {
    'AUD': 1.6543,
    'BGN': 1.9558,
    'BRL': 6.3412,
    'CAD': 1.4902,
    'CHF': 0.9331,
    'CNY': 7.6218,
    'CZK': 25.142,
    'DKK': 7.4601,
    'GBP': 0.8291,
    'HKD': 8.1503,
    'HUF': 412.35,
    'IDR': 16884.21,
    'ILS': 3.8127,
    'INR': 88.642,
    'ISK': 145.20,
    'JPY': 163.41,
    'KRW': 1521.08,
    'MXN': 21.337,
    'MYR': 4.6802,
    'NOK': 11.7415,
    'NZD': 1.8324,
    'PHP': 61.204,
    'PLN': 4.2611,
    'RON': 4.9748,
    'SEK': 11.4203,
    'SGD': 1.4108,
    'THB': 35.812,
    'TRY': 36.914,
    'USD': 1.0472,
    'ZAR': 19.204,
}


class StaticRateProvider:
    """Returns :data:`SAMPLE_RATES`, dated to a day you choose."""

    name = 'static'

    def __init__(
        self,
        rates: dict[str, float] | None = None,
        rate_date: date | None = None,
    ) -> None:
        self._rates = dict(rates or SAMPLE_RATES)
        self._rate_date = rate_date

    def fetch_latest(self) -> RateSnapshot:
        return RateSnapshot(
            rate_date=self._rate_date or date.today(),
            rates=dict(self._rates),
        )
