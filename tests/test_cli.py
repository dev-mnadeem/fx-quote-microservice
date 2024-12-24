"""The operator command line."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.cli import EXIT_FAILED, EXIT_OK, main
from app.config import Settings
from app.providers.base import RateProviderError
from app.services import RateService


def test_seed_stores_a_snapshot(
    session: Session, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(['seed']) == EXIT_OK

    assert RateService(session).latest_rate_date() is not None
    assert 'Stored' in capsys.readouterr().out


def test_seeding_twice_updates_rather_than_duplicating(
    session: Session, capsys: pytest.CaptureFixture[str]
) -> None:
    main(['seed'])
    capsys.readouterr()

    main(['seed'])

    assert '0 new' in capsys.readouterr().out


def test_seed_reports_an_upstream_failure_and_suggests_the_offline_source(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class Failing:
        name = 'ecb'

        def fetch_latest(self) -> None:
            raise RateProviderError('upstream is down')

    monkeypatch.setattr('app.cli.build_provider', lambda _s: Failing())

    assert main(['seed']) == EXIT_FAILED

    assert 'RATES_PROVIDER=static' in capsys.readouterr().err


def test_show_on_an_empty_database_points_at_seed(
    session: Session, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(['show']) == EXIT_OK

    assert 'python -m app.cli seed' in capsys.readouterr().out


def test_show_prints_the_latest_snapshot(
    two_snapshots: Session, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(['show']) == EXIT_OK

    output = capsys.readouterr().out
    assert 'Latest snapshot' in output
    assert 'USD' in output


def test_an_unknown_command_exits_rather_than_guessing() -> None:
    with pytest.raises(SystemExit):
        main(['dance'])


def test_settings_default_to_the_offline_friendly_cli_behaviour() -> None:
    assert Settings().rates_provider == 'ecb'
