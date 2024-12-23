"""Data access. Nothing above this layer writes SQLAlchemy queries."""

from app.repositories.exchange_rate import ExchangeRateRepository

__all__ = ['ExchangeRateRepository']
