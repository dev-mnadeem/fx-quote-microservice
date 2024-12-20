"""One row per (currency, publication date) of the euro reference rates."""

from __future__ import annotations

from sqlalchemy import Column, Date, Float, Index, String, UniqueConstraint

from app.db import Base

CURRENCY_CODE_LENGTH = 3


class ExchangeRate(Base):
    """Units of ``currency`` that one euro bought on ``rate_date``."""

    __tablename__ = 'exchange_rate'
    __table_args__ = (
        # Re-running ingest for a day must update, never duplicate.
        UniqueConstraint(
            'currency', 'rate_date', name='uq_exchange_rate_currency_date'
        ),
        # Serves "latest snapshot" and "history for one currency" alike.
        Index('ix_exchange_rate_date_currency', 'rate_date', 'currency'),
    )

    currency = Column(String(CURRENCY_CODE_LENGTH), nullable=False, index=True)
    rate_date = Column(Date, nullable=False, index=True)
    rate = Column(Float, nullable=False)
    # Absolute move against the previous published day. NULL on first sight.
    change = Column(Float, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f'<ExchangeRate {self.currency} {self.rate} @ {self.rate_date}>'
