"""Command line interface for the ¤_tapedeck_¤ music player.

usage: tapedeck [-h] [-c] [-v] {play,search} ...

positional arguments:
  {play,search}

optional arguments:
  -h, --help     show this help message and exit
  -c, --config   print the configuration and exit
  -v, --version  print the version and exit

"""
import argparse
import os
import sys

import trio

import tapedeck


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
        trio.run(args.func, args)


def enter():
    """Run synchronous for setuptools."""
    sys.exit(tapedeck_cli())


if __name__ == '__main__':
    enter()
