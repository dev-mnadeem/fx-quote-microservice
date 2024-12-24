"""The seam for "turn a sentence into a conversion request".

Two implementations ship: a deterministic parser that needs no network,
and a Claude-backed one. Both satisfy :class:`QueryInterpreter`, so the
route never learns which is in use.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class ConversionIntent:
    """What the user appears to have asked for."""

    source: str
    target: str
    amount: float
    interpreter: str

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError('amount must be positive')


@runtime_checkable
class QueryInterpreter(Protocol):
    """Parses a free-text question into a :class:`ConversionIntent`."""

    name: str

    def interpret(
        self, question: str, known_currencies: list[str]
    ) -> ConversionIntent | None:
        """Return the intent, or ``None`` if the question is not one."""
        ...
