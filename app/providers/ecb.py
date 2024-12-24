"""European Central Bank daily reference rates (the live source).

The ECB publishes one XML document a day, around 16:00 CET, on working days
only. The document carries its own publication date, which is why the
service stores ``rate_date`` rather than assuming "today".
"""

from __future__ import annotations

from datetime import date
from xml.etree import ElementTree

import httpx

from app.providers.base import RateProviderError, RateSnapshot

# The ECB namespaces its elements, and has changed the URI before now, so
# every path below matches any namespace.
_DATED_CUBE = './/{*}Cube[@time]'
_QUOTE_CUBE = './/{*}Cube[@currency]'


class EcbRateProvider:
    """Reads euro reference rates over HTTP."""

    name = 'ecb'

    def __init__(self, url: str, timeout_seconds: float) -> None:
        self._url = url
        self._timeout_seconds = timeout_seconds

    def fetch_latest(self) -> RateSnapshot:
        return parse_ecb_document(self._download())

    def _download(self) -> bytes:
        try:
            response = httpx.get(
                self._url,
                timeout=self._timeout_seconds,
                follow_redirects=True,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RateProviderError(
                f'could not read euro reference rates from {self._url}: {exc}'
            ) from exc
        return response.content


def parse_ecb_document(payload: bytes) -> RateSnapshot:
    """Turn one ECB ``eurofxref-daily`` document into a snapshot.

    Kept separate from the HTTP call so it can be tested against a fixture.
    """

    try:
        root = ElementTree.fromstring(payload)
    except ElementTree.ParseError as exc:
        raise RateProviderError(f'malformed ECB document: {exc}') from exc

    dated = root.find(_DATED_CUBE)
    if dated is None:
        raise RateProviderError('ECB document contains no dated cube')

    try:
        rate_date = date.fromisoformat(dated.attrib['time'])
    except ValueError as exc:
        raise RateProviderError(
            f'ECB document has an unparseable date: {exc}'
        ) from exc

    rates: dict[str, float] = {}
    for quote in dated.findall(_QUOTE_CUBE):
        code = quote.attrib['currency'].upper()
        try:
            rates[code] = float(quote.attrib['rate'])
        except (KeyError, ValueError) as exc:
            raise RateProviderError(
                f'ECB document has an unusable rate for {code}: {exc}'
            ) from exc

    if not rates:
        raise RateProviderError('ECB document contains no quotes')

    return RateSnapshot(rate_date=rate_date, rates=rates)
