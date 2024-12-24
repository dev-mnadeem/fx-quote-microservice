"""Converting money, either with explicit codes or in words."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import ConversionServiceDep, InterpreterDep
from app.schemas import AskRequest, AskResponse, ConversionOut, ErrorOut
from app.services.errors import UnparseableQuestionError

router = APIRouter(prefix='/v1/convert', tags=['convert'])

MIN_AMOUNT = 0.0

CurrencyQuery = Annotated[
    str,
    Query(min_length=3, max_length=3, examples=['USD']),
]

ERRORS = {
    404: {'model': ErrorOut, 'description': 'Unknown currency'},
    409: {'model': ErrorOut, 'description': 'Nothing ingested yet'},
    422: {'model': ErrorOut, 'description': 'Question not understood'},
}


@router.get(
    '',
    response_model=ConversionOut,
    responses=ERRORS,
    summary='Convert between two currencies',
)
async def convert(
    conversions: ConversionServiceDep,
    source: Annotated[
        str, Query(alias='from', min_length=3, max_length=3, examples=['USD'])
    ],
    target: Annotated[
        str, Query(alias='to', min_length=3, max_length=3, examples=['JPY'])
    ],
    amount: Annotated[float, Query(gt=MIN_AMOUNT)] = 1.0,
) -> ConversionOut:
    """Cross-rate conversion through the euro, at the latest rates."""

    return ConversionOut.model_validate(
        conversions.convert(source=source, target=target, amount=amount)
    )


@router.post(
    '/ask',
    response_model=AskResponse,
    responses=ERRORS,
    summary='Convert from a question in words',
)
async def ask(
    payload: AskRequest,
    conversions: ConversionServiceDep,
    interpreter: InterpreterDep,
) -> AskResponse:
    """Read a sentence such as "250 dollars in yen" and answer it.

    The interpreter only decides *what* was asked. The number itself still
    comes from the stored rates, so the answer is never invented.
    """

    intent = interpreter.interpret(
        payload.question, conversions.known_currencies()
    )
    if intent is None:
        raise UnparseableQuestionError(payload.question)

    return AskResponse(
        question=payload.question,
        interpreter=intent.interpreter,
        conversion=ConversionOut.model_validate(
            conversions.convert(
                source=intent.source,
                target=intent.target,
                amount=intent.amount,
            )
        ),
    )
