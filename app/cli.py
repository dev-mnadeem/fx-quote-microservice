"""Small command line for operating the service.

python -m app.cli seed      fetch the newest snapshot and store it
python -m app.cli show      print what is currently stored
"""

from __future__ import annotations

import argparse
import logging
import sys

from app.config import get_settings
from app.db import create_schema, session_scope
from app.providers import RateProviderError, build_provider
from app.services import RateService, ingest_from_provider

EXIT_OK = 0
EXIT_FAILED = 1
PREVIEW_ROWS = 5


def seed() -> int:
    """Fetch from the configured provider and store the result."""

    settings = get_settings()
    create_schema()
    provider = build_provider(settings)
    print(f'Fetching rates from the "{provider.name}" provider...')
    try:
        with session_scope() as session:
            result = ingest_from_provider(session, provider)
    except RateProviderError as exc:
        print(f'Could not fetch rates: {exc}', file=sys.stderr)
        print(
            'Tip: run with RATES_PROVIDER=static to seed offline.',
            file=sys.stderr,
        )
        return EXIT_FAILED

    print(
        f'Stored {result.total} quotes for {result.rate_date} '
        f'({result.inserted} new, {result.updated} updated).'
    )
    if result.compared_against is None:
        print('No earlier snapshot, so day-over-day change is empty.')
    else:
        print(f'Change computed against {result.compared_against}.')
    return EXIT_OK


def show() -> int:
    """Print a short summary of what is stored."""

    create_schema()
    with session_scope() as session:
        service = RateService(session)
        latest = service.latest_rate_date()
        if latest is None:
            print('Nothing stored yet. Run: python -m app.cli seed')
            return EXIT_OK
        page = service.list_latest(limit=PREVIEW_ROWS, offset=0)
        print(f'Latest snapshot: {latest} ({page.total} currencies)')
        for row in page.items:
            change = '   n/a' if row.change is None else f'{row.change:+.4f}'
            print(f'  1 EUR = {row.rate:>12.4f} {row.currency}  {change}')
        if page.has_more:
            print(f'  ... and {page.total - len(page.items)} more')
    return EXIT_OK


COMMANDS = {'seed': seed, 'show': show}


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    # httpx logs every request at INFO, which is noise in a CLI.
    logging.getLogger('httpx').setLevel(logging.WARNING)
    parser = argparse.ArgumentParser(prog='python -m app.cli')
    parser.add_argument('command', choices=sorted(COMMANDS))
    args = parser.parse_args(argv)
    return COMMANDS[args.command]()


if __name__ == '__main__':
    raise SystemExit(main())
