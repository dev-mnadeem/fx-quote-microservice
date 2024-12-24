"""The seam between "where rates come from" and "what we do with them".

Anything that can produce a dated set of euro reference rates satisfies
:class:`RateProvider`. Adding a second upstream means adding one module and
one registry entry -- no service or route changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Protocol, runtime_checkable

BASE_CURRENCY = 'EUR'


class RateProviderError(RuntimeError):
    """Upstream was unreachable or returned something unusable."""


@dataclass(frozen=True, slots=True)
class RateSnapshot:
    """All quotes published for a single day, keyed by ISO 4217 code.

    ``rates`` maps a currency code to the units of that currency bought by
    one euro. The base currency itself is never a key.
    """

    rate_date: date
    rates: dict[str, float] = field(default_factory=dict)
    base: str = BASE_CURRENCY

    def __post_init__(self) -> None:
        if not self.rates:
            raise ValueError('a snapshot must contain at least one rate')
        if self.base in self.rates:
            raise ValueError(
                f'the base currency {self.base} must not appear in rates'
            )

    @property
    def currencies(self) -> list[str]:
        return sorted(self.rates)


@runtime_checkable
class RateProvider(Protocol):
    """Fetches the most recent published snapshot."""

    name: str

    def fetch_latest(self) -> RateSnapshot:
        """Return the newest snapshot, or raise :class:`RateProviderError`."""
        ...
