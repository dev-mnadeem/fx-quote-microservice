"""Provider registry.

``build_provider`` is the only place that knows which names exist, so a new
upstream is one entry in :data:`_FACTORIES`.
"""

from __future__ import annotations

from collections.abc import Callable

from app.config import Settings, get_settings
from app.providers.base import (
    BASE_CURRENCY,
    RateProvider,
    RateProviderError,
    RateSnapshot,
)
from app.providers.ecb import EcbRateProvider, parse_ecb_document
from app.providers.static import StaticRateProvider

__all__ = [
    'BASE_CURRENCY',
    'EcbRateProvider',
    'RateProvider',
    'RateProviderError',
    'RateSnapshot',
    'StaticRateProvider',
    'available_providers',
    'build_provider',
    'parse_ecb_document',
]

_FACTORIES: dict[str, Callable[[Settings], RateProvider]] = {
    'ecb': lambda settings: EcbRateProvider(
        url=settings.ecb_url,
        timeout_seconds=settings.http_timeout_seconds,
    ),
    'static': lambda _settings: StaticRateProvider(),
}


def available_providers() -> list[str]:
    return sorted(_FACTORIES)


def build_provider(settings: Settings | None = None) -> RateProvider:
    """Instantiate the provider named by ``RATES_PROVIDER``."""

    settings = settings or get_settings()
    try:
        factory = _FACTORIES[settings.rates_provider]
    except KeyError as exc:
        raise ValueError(
            f'unknown RATES_PROVIDER {settings.rates_provider!r}; '
            f'expected one of {", ".join(available_providers())}'
        ) from exc
    return factory(settings)
