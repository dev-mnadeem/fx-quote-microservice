"""Turning a provider snapshot into stored rows.

The day-over-day ``change`` for every currency is computed from a single
query for the previous snapshot -- not one query per currency -- and the
whole day is written in one transaction.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.providers.base import RateProvider, RateSnapshot
from app.repositories import ExchangeRateRepository


@dataclass(frozen=True, slots=True)
class IngestResult:
    """What one ingest run did, for logs and for the CLI."""

    rate_date: date
    inserted: int
    updated: int
    compared_against: date | None

    @property
    def total(self) -> int:
        return self.inserted + self.updated


def compute_changes(
    rates: dict[str, float], previous: dict[str, float]
) -> dict[str, float | None]:
    """Absolute move per currency, ``None`` where there is no prior quote."""

    return {
        currency: (rate - previous[currency] if currency in previous else None)
        for currency, rate in rates.items()
    }


def ingest_snapshot(session: Session, snapshot: RateSnapshot) -> IngestResult:
    """Store one snapshot, computing each currency's day-over-day move."""

    repository = ExchangeRateRepository(session)
    previous_date = repository.previous_rate_date(snapshot.rate_date)
    previous = (
        repository.snapshot_rates(previous_date) if previous_date else {}
    )

    changes = compute_changes(snapshot.rates, previous)
    inserted, updated = repository.upsert_snapshot(
        snapshot.rate_date, snapshot.rates, changes
    )

    return IngestResult(
        rate_date=snapshot.rate_date,
        inserted=inserted,
        updated=updated,
        compared_against=previous_date,
    )


def ingest_from_provider(
    session: Session, provider: RateProvider
) -> IngestResult:
    """Fetch from ``provider`` and store the result."""

    return ingest_snapshot(session, provider.fetch_latest())
