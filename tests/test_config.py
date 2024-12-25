"""Configuration is read from the environment in exactly one place."""

from __future__ import annotations

import pytest

from app.config import (
    DEFAULT_ANTHROPIC_MODEL,
    DEFAULT_DATABASE_URL,
    Settings,
    load_settings,
)


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        'DATABASE_URL',
        'RATES_PROVIDER',
        'ECB_URL',
        'HTTP_TIMEOUT_SECONDS',
        'SCHEDULER_ENABLED',
        'INGEST_HOUR',
        'INGEST_MINUTE',
        'DEFAULT_PAGE_SIZE',
        'MAX_PAGE_SIZE',
        'NLQ_PROVIDER',
        'ANTHROPIC_API_KEY',
        'ANTHROPIC_MODEL',
    ):
        monkeypatch.delenv(name, raising=False)


def test_defaults_need_no_environment(clean_env: None) -> None:
    settings = load_settings()

    assert settings.database_url == DEFAULT_DATABASE_URL
    assert settings.rates_provider == 'ecb'
    assert settings.nlq_provider == 'rules'
    assert settings.anthropic_model == DEFAULT_ANTHROPIC_MODEL
    assert settings.anthropic_api_key is None
    assert settings.scheduler_enabled is True


def test_values_are_read_from_the_environment(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///./other.db')
    monkeypatch.setenv('RATES_PROVIDER', 'STATIC')
    monkeypatch.setenv('INGEST_HOUR', '6')
    monkeypatch.setenv('HTTP_TIMEOUT_SECONDS', '2.5')

    settings = load_settings()

    assert settings.database_url == 'sqlite:///./other.db'
    assert settings.rates_provider == 'static'
    assert settings.ingest_hour == 6
    assert settings.http_timeout_seconds == 2.5


@pytest.mark.parametrize(
    ('raw', 'expected'),
    [
        ('true', True),
        ('True', True),
        ('1', True),
        ('yes', True),
        ('on', True),
        ('false', False),
        ('0', False),
        ('anything else', False),
    ],
)
def test_boolean_parsing(
    clean_env: None,
    monkeypatch: pytest.MonkeyPatch,
    raw: str,
    expected: bool,
) -> None:
    monkeypatch.setenv('SCHEDULER_ENABLED', raw)

    assert load_settings().scheduler_enabled is expected


def test_blank_value_falls_back_to_the_default(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv('DATABASE_URL', '   ')

    assert load_settings().database_url == DEFAULT_DATABASE_URL


def test_a_non_numeric_integer_is_rejected_loudly(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv('INGEST_HOUR', 'midnight')

    with pytest.raises(ValueError, match='INGEST_HOUR'):
        load_settings()


def test_settings_are_immutable() -> None:
    settings = Settings()

    with pytest.raises(AttributeError):
        settings.database_url = 'sqlite:///./hijacked.db'


@pytest.mark.parametrize(
    ('url', 'expected'),
    [
        ('sqlite:///./exchange_rate.db', True),
        ('postgresql+psycopg://user@host/db', False),
    ],
)
def test_is_sqlite(url: str, expected: bool) -> None:
    assert Settings(database_url=url).is_sqlite is expected
