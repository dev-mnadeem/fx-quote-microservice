"""Reading euro reference rates."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.api.deps import (
    DEFAULT_HISTORY_POINTS,
    MAX_HISTORY_POINTS,
    MIN_HISTORY_POINTS,
    PaginationDep,
    RateServiceDep,
)
from app.providers.base import BASE_CURRENCY
from app.schemas import ErrorOut, HistoryOut, QuoteOut, RatePageOut

router = APIRouter(prefix='/v1/rates', tags=['rates'])

CurrencyPath = Annotated[
    str,
    Path(
        min_length=3,
        max_length=3,
        description='ISO 4217 code, for example USD.',
        examples=['USD'],
    ),
]

NOT_FOUND = {404: {'model': ErrorOut, 'description': 'Unknown currency'}}
NO_DATA = {409: {'model': ErrorOut, 'description': 'Nothing ingested yet'}}


@router.get(
    '',
    response_model=RatePageOut,
    responses=NO_DATA,
    summary='Latest published snapshot',
)
async def list_rates(
    rates: RateServiceDep,
    page: PaginationDep,
    currency: Annotated[
        list[str] | None,
        Query(description='Repeat to filter to specific codes.'),
    ] = None,
) -> RatePageOut:
    """Quotes from the newest publication date, one page at a time."""

    result = rates.list_latest(
        limit=page.limit, offset=page.offset, currencies=currency
    )
    return RatePageOut(
        rate_date=result.rate_date,
        base=result.base,
        total=result.total,
        limit=result.limit,
        offset=result.offset,
        has_more=result.has_more,
        rates=[QuoteOut.model_validate(row) for row in result.items],
    )


@router.get(
    '/{currency}',
    response_model=QuoteOut,
    responses=NOT_FOUND | NO_DATA,
    summary='Latest quote for one currency',
)
async def get_rate(currency: CurrencyPath, rates: RateServiceDep) -> QuoteOut:
    return QuoteOut.model_validate(rates.get_latest_quote(currency))


@router.get(
    '/{currency}/history',
    response_model=HistoryOut,
    responses=NOT_FOUND,
    summary='Recent quotes for one currency',
)
async def get_history(
    currency: CurrencyPath,
    rates: RateServiceDep,
    points: Annotated[
        int,
        Query(
            ge=MIN_HISTORY_POINTS,
            le=MAX_HISTORY_POINTS,
            description='How many publication dates to return.',
        ),
    ] = DEFAULT_HISTORY_POINTS,
) -> HistoryOut:
    rows = rates.history(currency, limit=points)
    return HistoryOut(
        currency=rows[0].currency,
        base=BASE_CURRENCY,
        points=list(rows),
    )
