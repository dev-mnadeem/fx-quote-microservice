"""Request and response models for the conversion endpoints."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

MAX_QUESTION_LENGTH = 300


class ConversionOut(BaseModel):
    """An amount moved from one currency to another."""

    model_config = ConfigDict(from_attributes=True)

    source: str
    target: str
    amount: float
    converted: float
    rate: float = Field(
        description='Units of target bought by one unit of source.'
    )
    rate_date: date
    base: str


class AskRequest(BaseModel):
    """A conversion asked for in words."""

    question: str = Field(
        min_length=1,
        max_length=MAX_QUESTION_LENGTH,
        examples=['how much is 250 dollars in japanese yen'],
    )


class AskResponse(BaseModel):
    question: str
    interpreter: str = Field(
        description='Which interpreter produced the reading.'
    )
    conversion: ConversionOut
