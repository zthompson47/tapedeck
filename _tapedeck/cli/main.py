"""Command line interface for the ¤_tapedeck_¤ music player."""
import argparse
import logging
import os

import trio

import tapedeck

LOG = logging.getLogger(__name__)


def tapedeck_cli() -> int:
    """Enter the tapedeck cli."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-c', '--config', action='store_true',
        help='print the configuration and exit'
    )
    parser.add_argument(
        '-v', '--version', action='store_true',
        help='print the version and exit'
    )
    subparsers = parser.add_subparsers()

    tdplay = subparsers.add_parser('play')
    tapedeck.cli.play.load_args(tdplay)

    tdsearch = subparsers.add_parser('search')
    tapedeck.cli.search.load_args(tdsearch)

    args = parser.parse_args()

    if args.version:
        print(tapedeck.__version__)
    elif args.config:
        for key, val in os.environ.items():
            if key.startswith('TAPEDECK_'):
                print(f'{key}={val}')
    elif hasattr(args, 'func') and args.func:
        try:
            trio.run(main, args.func, args)
        except trio.ClosedResourceError:
            LOG.debug('Ungrateful dumpling', exc_info=True)


async def main(func, args):
    """Launch main program tasks."""
    async with trio.open_nursery() as nursery:
        await func(args, nursery)


def enter():
    """Run synchronous for setuptools."""
    tapedeck_cli()


if __name__ == '__main__':
    enter()
