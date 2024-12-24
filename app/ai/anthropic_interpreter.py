"""Claude-backed interpreter, for questions the rule parser cannot reach.

This is strictly an upgrade path. It is off by default, the ``anthropic``
package is an optional dependency, and every failure -- missing package,
missing key, network error, malformed answer -- falls through to the
deterministic parser rather than surfacing an error to the caller.
"""

from __future__ import annotations

import logging

from app.ai.base import ConversionIntent
from app.ai.rules import RuleBasedInterpreter

logger = logging.getLogger(__name__)

MAX_TOKENS = 1024
TOOL_NAME = 'record_conversion'

SYSTEM_PROMPT = (
    'You extract currency conversion requests from short questions. '
    'Call the record_conversion tool exactly once with the ISO 4217 code '
    'the money starts in, the code it should end in, and the amount. '
    'If the question is not a currency conversion, set unclear to true.'
)

CONVERSION_TOOL: dict[str, object] = {
    'name': TOOL_NAME,
    'description': 'Record the conversion the question is asking for.',
    'strict': True,
    'input_schema': {
        'type': 'object',
        'properties': {
            'source': {
                'type': 'string',
                'description': 'ISO 4217 code the amount is currently in.',
            },
            'target': {
                'type': 'string',
                'description': 'ISO 4217 code the amount should end in.',
            },
            'amount': {
                'type': 'number',
                'description': 'Quantity to convert. Use 1 if unstated.',
            },
            'unclear': {
                'type': 'boolean',
                'description': 'True when this is not a conversion request.',
            },
        },
        'required': ['source', 'target', 'amount', 'unclear'],
        'additionalProperties': False,
    },
}


class AnthropicInterpreter:
    """Asks Claude, and quietly defers to the rule parser when it cannot."""

    name = 'anthropic'

    def __init__(
        self,
        api_key: str | None,
        model: str,
        fallback: RuleBasedInterpreter | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._fallback = fallback or RuleBasedInterpreter()

    def interpret(
        self, question: str, known_currencies: list[str]
    ) -> ConversionIntent | None:
        intent = self._ask_claude(question, known_currencies)
        if intent is not None:
            return intent
        return self._fallback.interpret(question, known_currencies)

    def _ask_claude(
        self, question: str, known_currencies: list[str]
    ) -> ConversionIntent | None:
        if not self._api_key:
            logger.info('ANTHROPIC_API_KEY is unset; using the rule parser')
            return None

        try:
            import anthropic
        except ImportError:
            logger.warning(
                'NLQ_PROVIDER=anthropic but the anthropic package is not '
                'installed; using the rule parser'
            )
            return None

        client = anthropic.Anthropic(api_key=self._api_key)
        codes = ', '.join(known_currencies) or 'any ISO 4217 code'
        try:
            response = client.messages.create(
                model=self._model,
                max_tokens=MAX_TOKENS,
                output_config={'effort': 'low'},
                system=SYSTEM_PROMPT,
                tools=[CONVERSION_TOOL],
                tool_choice={'type': 'tool', 'name': TOOL_NAME},
                messages=[
                    {
                        'role': 'user',
                        'content': (
                            f'Available currencies: {codes}.\n'
                            f'Question: {question}'
                        ),
                    }
                ],
            )
        except Exception:  # noqa: BLE001 - any failure must degrade, not 500
            logger.exception('Claude call failed; using the rule parser')
            return None

        return self._to_intent(response)

    def _to_intent(self, response: object) -> ConversionIntent | None:
        payload = _first_tool_input(response)
        if payload is None or payload.get('unclear'):
            return None
        try:
            return ConversionIntent(
                source=str(payload['source']).upper(),
                target=str(payload['target']).upper(),
                amount=float(payload['amount']),
                interpreter=self.name,
            )
        except (KeyError, TypeError, ValueError):
            logger.warning('Claude returned an unusable payload')
            return None


def _first_tool_input(response: object) -> dict[str, object] | None:
    """Pull the tool arguments out of a Messages API response."""

    for block in getattr(response, 'content', []) or []:
        if getattr(block, 'type', None) == 'tool_use':
            payload = getattr(block, 'input', None)
            if isinstance(payload, dict):
                return payload
    return None
