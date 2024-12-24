"""Application factory and error mapping.

Building the app in a function -- rather than at import time -- means the
test suite can create one per configuration, and importing the module has
no side effects on the database.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app import __version__
from app.api.routes import convert, health, rates
from app.config import Settings, get_settings
from app.db import create_schema
from app.scheduler import build_scheduler
from app.services.errors import (
    NoRatesAvailableError,
    ServiceError,
    UnknownCurrencyError,
    UnparseableQuestionError,
)

logger = logging.getLogger(__name__)

DESCRIPTION = (
    'Euro reference rates from the European Central Bank, stored daily '
    'and served as quotes, day-over-day moves and cross-rate conversions.'
)

# One place decides what each domain failure looks like over HTTP.
STATUS_FOR_ERROR: dict[type[ServiceError], int] = {
    UnknownCurrencyError: 404,
    NoRatesAvailableError: 409,
    UnparseableQuestionError: 422,
}
FALLBACK_STATUS = 400


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build a configured application instance."""

    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        create_schema()
        scheduler = (
            build_scheduler(settings) if settings.scheduler_enabled else None
        )
        if scheduler is not None:
            scheduler.start()
            logger.info('daily ingest scheduled')
        try:
            yield
        finally:
            if scheduler is not None:
                scheduler.shutdown(wait=False)

    app = FastAPI(
        title='Currency Exchange',
        description=DESCRIPTION,
        version=__version__,
        lifespan=lifespan,
    )

    @app.exception_handler(ServiceError)
    async def handle_service_error(
        _request: Request, exc: ServiceError
    ) -> JSONResponse:
        status_code = STATUS_FOR_ERROR.get(type(exc), FALLBACK_STATUS)
        return JSONResponse(
            status_code=status_code, content={'detail': str(exc)}
        )

    app.include_router(health.router)
    app.include_router(rates.router)
    app.include_router(convert.router)
    return app


app = create_app()
