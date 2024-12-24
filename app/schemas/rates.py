"""Response models for the rate endpoints."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class QuoteOut(BaseModel):
    """One currency on one publication date."""

    model_config = ConfigDict(from_attributes=True)

    currency: str = Field(examples=['USD'])
    rate: float = Field(
        description='Units of this currency bought by one euro.'
    )
    change: float | None = Field(
        default=None,
        description='Absolute move since the previous published day.',
    )
    rate_date: date


class RatePageOut(BaseModel):
    """A page of the most recent snapshot."""

    rate_date: date
    base: str = Field(examples=['EUR'])
    total: int = Field(description='Quotes matching the filter, all pages.')
    limit: int
    offset: int
    has_more: bool
    rates: list[QuoteOut]


class HistoryPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rate_date: date
    rate: float
    change: float | None = None


class HistoryOut(BaseModel):
    """Recent quotes for a single currency, newest first."""

    currency: str
    base: str
    points: list[HistoryPoint]


class HealthOut(BaseModel):
    status: str = Field(examples=['ok'])
    version: str
    database: str = Field(description='"reachable" or the reason it is not.')
    rates_provider: str
    nlq_interpreter: str
    latest_rate_date: date | None = None
    stored_currencies: int = 0


class ServiceIndexOut(BaseModel):
    service: str
    version: str
    base_currency: str
    docs: str
    endpoints: list[str]


class ErrorOut(BaseModel):
    detail: str
