"""The background ingest job."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.providers.base import RateProviderError
from app.scheduler import INGEST_JOB_ID, build_scheduler, run_ingest
from app.services import RateService


def test_the_scheduler_holds_exactly_the_ingest_job() -> None:
    scheduler = build_scheduler(Settings())

    jobs = scheduler.get_jobs()

    assert [job.id for job in jobs] == [INGEST_JOB_ID]


def test_the_cron_trigger_uses_the_configured_time() -> None:
    scheduler = build_scheduler(Settings(ingest_hour=6, ingest_minute=45))

    trigger = str(scheduler.get_jobs()[0].trigger)

    assert "hour='6'" in trigger
    assert "minute='45'" in trigger


def test_running_the_job_stores_a_snapshot(session: Session) -> None:
    run_ingest(get_settings())

    assert RateService(session).latest_rate_date() is not None


def test_a_provider_failure_is_logged_not_raised(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(_settings: Settings) -> None:
        raise RateProviderError('upstream is down')

    monkeypatch.setattr('app.scheduler.build_provider', explode)

    run_ingest(get_settings())

    assert RateService(session).latest_rate_date() is None


def test_a_misconfigured_provider_is_logged_not_raised(
    session: Session,
) -> None:
    run_ingest(Settings(rates_provider='nonsense'))

    assert RateService(session).latest_rate_date() is None
