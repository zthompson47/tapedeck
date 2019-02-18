"""Command line interface to ``tapedeck``."""
import argparse
import logging
import sys

import blessings
import trio

import tapedeck
from . import play, search

LOG = logging.getLogger(__name__)
T = blessings.Terminal()


def tapedeck_cli() -> int:
    """Enter the tapedeck cli."""
    parser = argparse.ArgumentParser()

    # o=~ TAPEDECK ~=o

    parser.add_argument(
        '-c', '--config', action='store_true',
        help='print the configuration and exit'
    )
    parser.add_argument(
        '-v', '--version', action='store_true',
        help='print the version and exit'
    )
    subparsers = parser.add_subparsers()

    # o=~ TDPLAY ~=o

    tdplay = subparsers.add_parser('play')
    tdplay.add_argument('track', metavar='TRACK', nargs='?')
    tdplay.add_argument(
        '-o', '--output', default='speakers',
        help='output destination'
    )
    tdplay.add_argument(
        '-s', '--shuffle', action='store_true', help='shuffle order of tracks'
    )
    tdplay.add_argument(
        '-r', '--recursive', action='store_true', help='play subfolders'
    )
    tdplay.add_argument(
        '-m', '--memory', metavar='MEMORY', type=int,
        help='play track number from last search'
    )
    tdplay.add_argument(
        '--host', type=str, help='network streaming host'
    )
    tdplay.add_argument(
        '--port', type=str, help='network streaming port'
    )
    tdplay.set_defaults(func=play.play)

    # o=~ TDSEARCH ~=o

    tdsearch = subparsers.add_parser('search')
    tdsearch.add_argument('directory', metavar='DIRECTORY', nargs='?')
    tdsearch.add_argument(
        '-d', '--follow-dots', action='store_true',
        help='search hidden dot-directories'
    )
    tdsearch.add_argument(
        '-l', '--follow-links', action='store_true',
        help='search symlinked directories'
    )
    tdsearch.add_argument(
        '-m', '--memory', action='store_true',
        help='print last search and exit'
    )
    tdsearch.set_defaults(func=search.search)

    args = parser.parse_args()
    if args.version:
        print(f'{T.blue}¤_tapedeck_¤ ', end='')
        print(f'{T.yellow}v{tapedeck.__version__}{T.normal}')
    elif args.config:
        for key, val in trio.run(tapedeck.config.env).items():
            print(f'{T.blue}{key}{T.normal}={T.yellow}{val}{T.normal}')
    elif hasattr(args, 'func') and args.func:
        trio.run(args.func, args)


def enter():
    """Run sync for setuptools."""
    sys.exit(tapedeck_cli())


if __name__ == '__main__':
    enter()
