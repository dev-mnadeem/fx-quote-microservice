"""Domain errors. The API layer maps these to status codes in one place."""

from __future__ import annotations


class ServiceError(Exception):
    """Base class for every error the service raises deliberately."""


class NoRatesAvailableError(ServiceError):
    """Nothing has been ingested yet, so no question can be answered."""

    def __init__(self) -> None:
        super().__init__(
            'no exchange rates have been ingested yet -- '
            'run "python -m app.cli seed" first'
        )


class UnknownCurrencyError(ServiceError):
    """A currency code is not present in the latest snapshot."""

    def __init__(self, currency: str) -> None:
        self.currency = currency
        super().__init__(f'no rate is published for currency {currency!r}')


class UnparseableQuestionError(ServiceError):
    """A natural-language question could not be turned into a conversion."""

    def __init__(self, question: str) -> None:
        self.question = question
        super().__init__(
            'could not work out which currencies to convert between'
        )
