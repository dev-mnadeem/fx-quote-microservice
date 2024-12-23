"""All SQL touching the ``exchange_rate`` table.

Every method that answers "the whole snapshot" does so in one query; the
ingest path in particular must not run a lookup per currency.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ExchangeRate


class ExchangeRateRepository:
    """Reads and writes euro reference rates."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ---------------------------------------------------------------- reads

    def latest_rate_date(self) -> date | None:
        """Publication date of the newest stored snapshot."""

        return self._session.execute(
            select(func.max(ExchangeRate.rate_date))
        ).scalar_one_or_none()

    def previous_rate_date(self, before: date) -> date | None:
        """Publication date of the snapshot immediately before ``before``."""

        return self._session.execute(
            select(func.max(ExchangeRate.rate_date)).where(
                ExchangeRate.rate_date < before
            )
        ).scalar_one_or_none()

    def snapshot_rates(self, rate_date: date) -> dict[str, float]:
        """Every quote for one day, as a dict -- a single query."""

        rows = self._session.execute(
            select(ExchangeRate.currency, ExchangeRate.rate).where(
                ExchangeRate.rate_date == rate_date
            )
        ).all()
        return {row.currency: row.rate for row in rows}

    def snapshot_rows(self, rate_date: date) -> list[ExchangeRate]:
        """Model instances for one day, so ingest can update in place."""

        return list(
            self._session.execute(
                select(ExchangeRate).where(ExchangeRate.rate_date == rate_date)
            ).scalars()
        )

    def count_for_date(
        self, rate_date: date, currencies: list[str] | None = None
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(ExchangeRate)
            .where(ExchangeRate.rate_date == rate_date)
        )
        if currencies:
            stmt = stmt.where(ExchangeRate.currency.in_(currencies))
        return int(self._session.execute(stmt).scalar_one())

    def page_for_date(
        self,
        rate_date: date,
        limit: int,
        offset: int,
        currencies: list[str] | None = None,
    ) -> list[ExchangeRate]:
        """One page of a snapshot, ordered by currency for stable paging."""

        stmt = select(ExchangeRate).where(ExchangeRate.rate_date == rate_date)
        if currencies:
            stmt = stmt.where(ExchangeRate.currency.in_(currencies))
        stmt = (
            stmt.order_by(ExchangeRate.currency.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(self._session.execute(stmt).scalars())

    def get_quote(self, currency: str, rate_date: date) -> ExchangeRate | None:
        return self._session.execute(
            select(ExchangeRate).where(
                ExchangeRate.currency == currency,
                ExchangeRate.rate_date == rate_date,
            )
        ).scalar_one_or_none()

    def history(self, currency: str, limit: int) -> list[ExchangeRate]:
        """Most recent ``limit`` quotes for one currency, newest first."""

        return list(
            self._session.execute(
                select(ExchangeRate)
                .where(ExchangeRate.currency == currency)
                .order_by(ExchangeRate.rate_date.desc())
                .limit(limit)
            ).scalars()
        )

    def distinct_currencies(self) -> list[str]:
        return list(
            self._session.execute(
                select(ExchangeRate.currency)
                .distinct()
                .order_by(ExchangeRate.currency.asc())
            ).scalars()
        )

    # --------------------------------------------------------------- writes

    def upsert_snapshot(
        self,
        rate_date: date,
        rates: dict[str, float],
        changes: dict[str, float | None],
    ) -> tuple[int, int]:
        """Write a whole day at once. Returns ``(inserted, updated)``.

        Existing rows for the same day are updated rather than duplicated,
        which makes re-running ingest harmless.
        """

        existing = {row.currency: row for row in self.snapshot_rows(rate_date)}
        inserted = updated = 0

        for currency, rate in rates.items():
            row = existing.get(currency)
            if row is None:
                self._session.add(
                    ExchangeRate(
                        currency=currency,
                        rate_date=rate_date,
                        rate=rate,
                        change=changes.get(currency),
                    )
                )
                inserted += 1
            else:
                row.rate = rate
                row.change = changes.get(currency)
                updated += 1

        self._session.commit()
        return inserted, updated
