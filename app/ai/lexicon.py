"""Names, symbols and codes for the currencies the ECB publishes.

Only used by the deterministic parser. Keeping it as plain data means a
new alias is a one-line change and needs no model call to verify.
"""

from __future__ import annotations

# code -> the words people actually type for it
CURRENCY_NAMES: dict[str, tuple[str, ...]] = {
    'EUR': ('euro', 'euros', 'eur'),
    'USD': ('dollar', 'dollars', 'us dollar', 'us dollars', 'usd', 'bucks'),
    'GBP': ('pound', 'pounds', 'sterling', 'pound sterling', 'quid'),
    'JPY': ('yen', 'japanese yen'),
    'CHF': ('swiss franc', 'swiss francs', 'franc', 'francs'),
    'AUD': ('australian dollar', 'australian dollars', 'aussie dollar'),
    'CAD': ('canadian dollar', 'canadian dollars', 'loonie'),
    'NZD': ('new zealand dollar', 'new zealand dollars', 'kiwi dollar'),
    'SEK': ('swedish krona', 'swedish kronor'),
    'NOK': ('norwegian krone', 'norwegian kroner'),
    'DKK': ('danish krone', 'danish kroner'),
    'ISK': ('icelandic krona', 'icelandic kronur'),
    'CZK': ('czech koruna', 'czech korunas'),
    'PLN': ('zloty', 'zlotys', 'polish zloty'),
    'HUF': ('forint', 'forints', 'hungarian forint'),
    'RON': ('romanian leu', 'romanian lei'),
    'BGN': ('bulgarian lev', 'bulgarian leva', 'lev'),
    'TRY': ('turkish lira', 'lira'),
    'INR': ('rupee', 'rupees', 'indian rupee', 'indian rupees'),
    'CNY': ('yuan', 'renminbi', 'chinese yuan'),
    'HKD': ('hong kong dollar', 'hong kong dollars'),
    'SGD': ('singapore dollar', 'singapore dollars'),
    'KRW': ('won', 'korean won', 'south korean won'),
    'IDR': ('rupiah', 'indonesian rupiah'),
    'MYR': ('ringgit', 'malaysian ringgit'),
    'PHP': ('peso', 'philippine peso', 'philippine pesos'),
    'THB': ('baht', 'thai baht'),
    'ILS': ('shekel', 'shekels', 'israeli shekel'),
    'ZAR': ('rand', 'south african rand'),
    'BRL': ('real', 'reais', 'brazilian real'),
    'MXN': ('mexican peso', 'mexican pesos'),
}

# Symbols are matched literally, so each maps to exactly one code.
CURRENCY_SYMBOLS: dict[str, str] = {
    '€': 'EUR',
    '$': 'USD',
    '£': 'GBP',
    '¥': 'JPY',
    '₹': 'INR',
    '₩': 'KRW',
    '₪': 'ILS',
    '₺': 'TRY',
}

# A currency introduced by one of these is where the money starts, even
# when it is not the first one named: "how many yen from 100 dollars".
SOURCE_MARKERS: frozenset[str] = frozenset({'from'})


def name_aliases() -> dict[str, str]:
    """Flat ``alias -> code`` map, lower-cased."""

    aliases: dict[str, str] = {}
    for code, names in CURRENCY_NAMES.items():
        for name in names:
            aliases[name.lower()] = code
    return aliases


def known_codes() -> frozenset[str]:
    return frozenset(CURRENCY_NAMES)
