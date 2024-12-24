"""Reading stored rates: the latest snapshot, one quote, one history.

"Latest" means the newest *published* date in the table, never "today".
The ECB does not publish at weekends or on target holidays, so a query
pinned to today's date returns nothing for two days out of seven.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.models import ExchangeRate
from app.providers.base import BASE_CURRENCY
from app.repositories import ExchangeRateRepository
from app.services.errors import NoRatesAvailableError, UnknownCurrencyError


@dataclass(frozen=True, slots=True)
class RatePage:
    """One page of a snapshot plus the numbers needed to page through it."""

    rate_date: date
    base: str
    items: list[ExchangeRate]
    total: int
    limit: int
    offset: int

    @property
    def has_more(self) -> bool:
        return self.offset + len(self.items) < self.total


class RateService:
    """Query side of the service. Routes call this, never the repository."""

    def __init__(self, session: Session) -> None:
        self._repository = ExchangeRateRepository(session)

    def latest_rate_date(self) -> date | None:
        return self._repository.latest_rate_date()

    def require_latest_rate_date(self) -> date:
        rate_date = self._repository.latest_rate_date()
        if rate_date is None:
            raise NoRatesAvailableError
        return rate_date

    def list_latest(
        self,
        limit: int,
        offset: int,
        currencies: list[str] | None = None,
    ) -> RatePage:
        """A page of the newest published snapshot."""

        rate_date = self.require_latest_rate_date()
        normalised = normalise_codes(currencies) if currencies else None
        return RatePage(
            rate_date=rate_date,
            base=BASE_CURRENCY,
            items=self._repository.page_for_date(
                rate_date, limit=limit, offset=offset, currencies=normalised
            ),
            total=self._repository.count_for_date(rate_date, normalised),
            limit=limit,
            offset=offset,
        )

    def get_latest_quote(self, currency: str) -> ExchangeRate:
        """The newest quote for one currency."""

        code = normalise_code(currency)
        rate_date = self.require_latest_rate_date()
        quote = self._repository.get_quote(code, rate_date)
        if quote is None:
            raise UnknownCurrencyError(code)
        return quote

    def history(self, currency: str, limit: int) -> list[ExchangeRate]:
        """Recent quotes for one currency, newest first."""

        code = normalise_code(currency)
        rows = self._repository.history(code, limit)
        if not rows:
            raise UnknownCurrencyError(code)
        return rows

    def latest_snapshot_rates(self) -> tuple[date, dict[str, float]]:
        """Whole newest snapshot as a dict -- the input to conversion."""

        rate_date = self.require_latest_rate_date()
        return rate_date, self._repository.snapshot_rates(rate_date)

    def known_currencies(self) -> list[str]:
        """Every code ever stored, plus the base currency."""

        codes = set(self._repository.distinct_currencies())
        codes.add(BASE_CURRENCY)
        return sorted(codes)


def normalise_code(currency: str) -> str:
    return currency.strip().upper()


def normalise_codes(currencies: list[str]) -> list[str]:
    seen: dict[str, None] = {}
    for currency in currencies:
        code = normalise_code(currency)
        if code:
            seen[code] = None
    return list(seen)
