"""Natural-language front door for the conversion endpoint.

``build_interpreter`` is the registry: one entry per implementation.
"""

from __future__ import annotations

from collections.abc import Callable

from app.ai.anthropic_interpreter import AnthropicInterpreter
from app.ai.base import ConversionIntent, QueryInterpreter
from app.ai.rules import RuleBasedInterpreter
from app.config import Settings, get_settings

__all__ = [
    'AnthropicInterpreter',
    'ConversionIntent',
    'QueryInterpreter',
    'RuleBasedInterpreter',
    'available_interpreters',
    'build_interpreter',
]

_FACTORIES: dict[str, Callable[[Settings], QueryInterpreter]] = {
    'rules': lambda _settings: RuleBasedInterpreter(),
    'anthropic': lambda settings: AnthropicInterpreter(
        api_key=settings.anthropic_api_key,
        model=settings.anthropic_model,
    ),
}


def available_interpreters() -> list[str]:
    return sorted(_FACTORIES)


def build_interpreter(
    settings: Settings | None = None,
) -> QueryInterpreter:
    """Instantiate the interpreter named by ``NLQ_PROVIDER``."""

    settings = settings or get_settings()
    try:
        factory = _FACTORIES[settings.nlq_provider]
    except KeyError as exc:
        raise ValueError(
            f'unknown NLQ_PROVIDER {settings.nlq_provider!r}; '
            f'expected one of {", ".join(available_interpreters())}'
        ) from exc
    return factory(settings)
