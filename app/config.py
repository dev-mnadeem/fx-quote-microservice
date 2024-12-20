"""Every environment-tunable value in the service lives here.

Nothing else in the package reads ``os.environ``. Call :func:`get_settings`
to obtain the cached, immutable snapshot.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

DEFAULT_DATABASE_URL = 'sqlite:///./exchange_rate.db'
DEFAULT_ECB_URL = (
    'https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml'
)
DEFAULT_HTTP_TIMEOUT_SECONDS = 10.0
DEFAULT_INGEST_HOUR = 0
DEFAULT_INGEST_MINUTE = 2
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200
DEFAULT_ANTHROPIC_MODEL = 'claude-opus-5'

_TRUTHY = frozenset({'1', 'true', 'yes', 'on'})


def _env_str(name: str, default: str) -> str:
    value = os.environ.get(name, '').strip()
    return value or default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, '').strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f'{name} must be an integer, got {raw!r}') from exc


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, '').strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f'{name} must be a number, got {raw!r}') from exc


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name, '').strip().lower()
    if not raw:
        return default
    return raw in _TRUTHY


@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable view of the process configuration."""

    database_url: str = DEFAULT_DATABASE_URL
    rates_provider: str = 'ecb'
    ecb_url: str = DEFAULT_ECB_URL
    http_timeout_seconds: float = DEFAULT_HTTP_TIMEOUT_SECONDS
    scheduler_enabled: bool = True
    ingest_hour: int = DEFAULT_INGEST_HOUR
    ingest_minute: int = DEFAULT_INGEST_MINUTE
    default_page_size: int = DEFAULT_PAGE_SIZE
    max_page_size: int = MAX_PAGE_SIZE
    nlq_provider: str = 'rules'
    anthropic_api_key: str | None = None
    anthropic_model: str = DEFAULT_ANTHROPIC_MODEL

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith('sqlite')


def load_settings() -> Settings:
    """Read configuration from the environment, applying defaults."""

    return Settings(
        database_url=_env_str('DATABASE_URL', DEFAULT_DATABASE_URL),
        rates_provider=_env_str('RATES_PROVIDER', 'ecb').lower(),
        ecb_url=_env_str('ECB_URL', DEFAULT_ECB_URL),
        http_timeout_seconds=_env_float(
            'HTTP_TIMEOUT_SECONDS', DEFAULT_HTTP_TIMEOUT_SECONDS
        ),
        scheduler_enabled=_env_bool('SCHEDULER_ENABLED', True),
        ingest_hour=_env_int('INGEST_HOUR', DEFAULT_INGEST_HOUR),
        ingest_minute=_env_int('INGEST_MINUTE', DEFAULT_INGEST_MINUTE),
        default_page_size=_env_int('DEFAULT_PAGE_SIZE', DEFAULT_PAGE_SIZE),
        max_page_size=_env_int('MAX_PAGE_SIZE', MAX_PAGE_SIZE),
        nlq_provider=_env_str('NLQ_PROVIDER', 'rules').lower(),
        anthropic_api_key=os.environ.get('ANTHROPIC_API_KEY') or None,
        anthropic_model=_env_str('ANTHROPIC_MODEL', DEFAULT_ANTHROPIC_MODEL),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings, so the environment is parsed exactly once."""

    return load_settings()
