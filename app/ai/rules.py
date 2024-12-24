"""A deterministic natural-language parser -- the default interpreter.

It recognises an amount, two currencies and the direction between them.
There is no model call, no API key and no network, so the endpoint works
out of the box and its behaviour is fully covered by the test suite.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.ai.base import ConversionIntent
from app.ai.lexicon import (
    CURRENCY_SYMBOLS,
    SOURCE_MARKERS,
    known_codes,
    name_aliases,
)

DEFAULT_AMOUNT = 1.0
MULTIPLIERS = {'k': 1_000.0, 'm': 1_000_000.0, 'bn': 1_000_000_000.0}
_REQUIRED_CURRENCIES = 2

_AMOUNT = re.compile(
    r'(?<![\w.])(\d[\d,]*(?:\.\d+)?)\s*(bn|[km])?\b', re.IGNORECASE
)
# ISO codes are matched upper-case only. Lower-cased, several of them are
# ordinary English words -- "try", "all", "cup" -- and would fire on
# sentences that mention no currency at all.
_ISO_CODE = re.compile(r'\b[A-Z]{3}\b')
_WORDS_BEFORE = re.compile(r'([A-Za-z]+)\W*(?:[\d,.]+\W*)?$')


@dataclass(frozen=True, slots=True)
class _Mention:
    start: int
    end: int
    code: str


def _name_pattern() -> re.Pattern[str]:
    # Longest alias first so "us dollar" wins over "dollar".
    aliases = sorted(name_aliases(), key=len, reverse=True)
    joined = '|'.join(re.escape(alias) for alias in aliases)
    return re.compile(rf'\b(?:{joined})\b')


_NAMES = _name_pattern()
_ALIAS_TO_CODE = name_aliases()


def parse_amount(question: str) -> float:
    """First number in the sentence, honouring ``k``/``m``/``bn``."""

    match = _AMOUNT.search(question)
    if match is None:
        return DEFAULT_AMOUNT
    value = float(match.group(1).replace(',', ''))
    suffix = (match.group(2) or '').lower()
    return value * MULTIPLIERS.get(suffix, 1.0)


def find_currency_mentions(question: str) -> list[_Mention]:
    """Every currency reference in the sentence, in reading order."""

    lowered = question.lower()
    found: list[_Mention] = []

    for match in _ISO_CODE.finditer(question):
        if match.group() in known_codes():
            found.append(_Mention(match.start(), match.end(), match.group()))

    for match in _NAMES.finditer(lowered):
        found.append(
            _Mention(match.start(), match.end(), _ALIAS_TO_CODE[match.group()])
        )

    for index, character in enumerate(question):
        code = CURRENCY_SYMBOLS.get(character)
        if code is not None:
            found.append(_Mention(index, index + 1, code))

    return _dedupe(found)


def _dedupe(mentions: list[_Mention]) -> list[_Mention]:
    """Drop overlapping and immediately repeated mentions."""

    ordered = sorted(mentions, key=lambda m: (m.start, -(m.end - m.start)))
    kept: list[_Mention] = []
    for mention in ordered:
        if kept and mention.start < kept[-1].end:
            continue  # overlaps a longer match already accepted
        if kept and mention.code == kept[-1].code:
            continue  # "usd to usd dollars"
        kept.append(mention)
    return kept


def _word_before(question: str, position: int) -> str:
    """Nearest preceding word, stepping over an intervening number.

    In "how many yen from 100 dollars" the word that matters before
    "dollars" is "from", not "100".
    """

    match = _WORDS_BEFORE.search(question[:position])
    return match.group(1).lower() if match else ''


def _orient(
    question: str, first: _Mention, second: _Mention
) -> tuple[str, str]:
    """Decide which mention is the source.

    Reading order is right nearly always ("100 USD in JPY"). The exception
    is a sentence that names the destination first -- "how many yen from
    100 dollars" -- which the word "from" gives away.
    """

    if _word_before(question, second.start) in SOURCE_MARKERS:
        return second.code, first.code
    return first.code, second.code


class RuleBasedInterpreter:
    """Offline interpreter. Always available, never calls out."""

    name = 'rules'

    def interpret(
        self, question: str, known_currencies: list[str]
    ) -> ConversionIntent | None:
        mentions = find_currency_mentions(question)
        if known_currencies:
            allowed = set(known_currencies)
            mentions = [m for m in mentions if m.code in allowed]
        if len(mentions) < _REQUIRED_CURRENCIES:
            return None

        source, target = _orient(question, mentions[0], mentions[1])
        if source == target:
            return None

        return ConversionIntent(
            source=source,
            target=target,
            amount=parse_amount(question),
            interpreter=self.name,
        )
