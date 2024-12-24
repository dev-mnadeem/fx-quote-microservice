"""The nightly ingest job.

The ECB publishes once per working day; the job runs shortly after
midnight so the service is already holding the newest snapshot by the time
anyone asks for it. Ingest is idempotent, so a repeated or retried run
updates the day's rows instead of duplicating them.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import Settings
from app.db import session_scope
from app.providers import RateProviderError, build_provider
from app.services import ingest_from_provider

logger = logging.getLogger(__name__)

INGEST_JOB_ID = 'daily-rate-ingest'


def run_ingest(settings: Settings) -> None:
    """Fetch the newest snapshot and store it. Never raises."""

    try:
        provider = build_provider(settings)
        with session_scope() as session:
            result = ingest_from_provider(session, provider)
    except (RateProviderError, ValueError):
        logger.exception('rate ingest failed')
        return

    logger.info(
        'ingested %s: %d new, %d updated (previous snapshot %s)',
        result.rate_date,
        result.inserted,
        result.updated,
        result.compared_against,
    )


def build_scheduler(settings: Settings) -> BackgroundScheduler:
    """A scheduler holding the single ingest job."""

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_ingest,
        CronTrigger(hour=settings.ingest_hour, minute=settings.ingest_minute),
        args=[settings],
        id=INGEST_JOB_ID,
        replace_existing=True,
    )
    return scheduler
