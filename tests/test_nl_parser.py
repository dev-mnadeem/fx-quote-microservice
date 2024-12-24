"""The deterministic natural-language parser.

These are the cases the endpoint is claimed to handle, so they are all
asserted rather than described.
"""

from __future__ import annotations

import pytest

from app.ai import (
    AnthropicInterpreter,
    RuleBasedInterpreter,
    available_interpreters,
    build_interpreter,
)
from app.ai.rules import find_currency_mentions, parse_amount
from app.config import Settings

ALL_CODES: list[str] = []


@pytest.fixture
def interpreter() -> RuleBasedInterpreter:
    return RuleBasedInterpreter()


@pytest.mark.parametrize(
    ('question', 'expected'),
    [
        ('how much is 250 dollars in japanese yen', 250.0),
        ('convert 1,250.50 USD to GBP', 1250.5),
        ('what is 2k euros in dollars', 2000.0),
        ('3m JPY in USD', 3_000_000.0),
        ('1bn yen in euros', 1_000_000_000.0),
        ('dollars to yen', 1.0),
    ],
)
def test_amount_parsing(question: str, expected: float) -> None:
    assert parse_amount(question) == expected


@pytest.mark.parametrize(
    ('question', 'source', 'target'),
    [
        ('how much is 250 dollars in japanese yen', 'USD', 'JPY'),
        ('convert 100 USD to GBP', 'USD', 'GBP'),
        ('$50 in euros', 'USD', 'EUR'),
        ('£20 to swiss francs', 'GBP', 'CHF'),
        ('900 yen as pounds', 'JPY', 'GBP'),
        ('turn 5 euros into indian rupees', 'EUR', 'INR'),
        ('1000 hungarian forint in polish zloty', 'HUF', 'PLN'),
        ('10 canadian dollars in australian dollars', 'CAD', 'AUD'),
    ],
)
def test_direction_follows_reading_order(
    interpreter: RuleBasedInterpreter,
    question: str,
    source: str,
    target: str,
) -> None:
    intent = interpreter.interpret(question, ALL_CODES)

    assert intent is not None
    assert (intent.source, intent.target) == (source, target)


def test_a_destination_first_question_is_reoriented(
    interpreter: RuleBasedInterpreter,
) -> None:
    intent = interpreter.interpret('how many yen from 100 dollars', ALL_CODES)

    assert intent is not None
    assert (intent.source, intent.target) == ('USD', 'JPY')


def test_the_longest_alias_wins(interpreter: RuleBasedInterpreter) -> None:
    intent = interpreter.interpret('5 us dollars in yen', ALL_CODES)

    assert intent is not None
    assert intent.source == 'USD'


def test_lower_case_iso_codes_are_not_mistaken_for_english_words() -> None:
    """ "try" is the Turkish lira in caps and a verb in lower case."""

    mentions = find_currency_mentions('let me try that in euros')

    assert [mention.code for mention in mentions] == ['EUR']


def test_an_upper_case_iso_code_still_matches() -> None:
    mentions = find_currency_mentions('100 TRY in EUR')

    assert [mention.code for mention in mentions] == ['TRY', 'EUR']


def test_a_repeated_currency_counts_once() -> None:
    mentions = find_currency_mentions('USD dollars to yen')

    assert [mention.code for mention in mentions] == ['USD', 'JPY']


@pytest.mark.parametrize(
    'question',
    [
        'what is the weather today',
        'how much is 100 dollars',
        'convert 5 yen to yen',
        '',
    ],
)
def test_questions_that_are_not_conversions_return_none(
    interpreter: RuleBasedInterpreter, question: str
) -> None:
    assert interpreter.interpret(question, ALL_CODES) is None


def test_currencies_outside_the_stored_set_are_ignored(
    interpreter: RuleBasedInterpreter,
) -> None:
    intent = interpreter.interpret(
        '100 dollars in yen', known_currencies=['USD', 'EUR']
    )

    assert intent is None


def test_the_intent_records_which_interpreter_read_it(
    interpreter: RuleBasedInterpreter,
) -> None:
    intent = interpreter.interpret('100 USD in JPY', ALL_CODES)

    assert intent is not None
    assert intent.interpreter == 'rules'


def test_registry_lists_both_interpreters() -> None:
    assert available_interpreters() == ['anthropic', 'rules']


def test_build_interpreter_defaults_to_the_offline_parser() -> None:
    assert isinstance(build_interpreter(Settings()), RuleBasedInterpreter)


def test_build_interpreter_can_select_claude() -> None:
    chosen = build_interpreter(Settings(nlq_provider='anthropic'))

    assert isinstance(chosen, AnthropicInterpreter)


def test_an_unknown_interpreter_names_the_valid_options() -> None:
    with pytest.raises(ValueError, match='anthropic, rules'):
        build_interpreter(Settings(nlq_provider='magic'))


def test_claude_falls_back_to_the_rules_parser_without_a_key() -> None:
    """No API key must degrade to the offline parser, not fail."""

    chosen = AnthropicInterpreter(api_key=None, model='claude-opus-5')

    intent = chosen.interpret('250 dollars in yen', ALL_CODES)

    assert intent is not None
    assert intent.interpreter == 'rules'
    assert (intent.source, intent.target) == ('USD', 'JPY')
