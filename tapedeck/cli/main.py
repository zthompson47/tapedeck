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
import logging
import sys

import blessings
import trio

import tapedeck

LOG_LEVEL = trio.run(tapedeck.config.env, 'TAPEDECK_LOG_LEVEL')
if LOG_LEVEL:
    LOG_FILE = trio.run(tapedeck.config.logfile, 'tapedeck.log')
    logging.basicConfig(level=LOG_LEVEL, filename=LOG_FILE)
LOG = logging.getLogger(__name__)
# LOG.addHandler(logging.StreamHandler(sys.stderr))
LOG.debug('[o_ NOW LOGGING tapedeck.cli.main _o]')

T = blessings.Terminal()


def tapedeck_cli() -> int:
    """Enter the tapedeck cli."""
    LOG.debug('YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY')
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
        # print(f'{T.blue}¤_tapedeck_¤ ', end='')
        # print(f'{T.yellow}v{tapedeck.__version__}{T.normal}')
        print(tapedeck.__version__)
    elif args.config:
        for key, val in trio.run(tapedeck.config.env).items():
            print(f'{T.blue}{key}{T.normal}={T.yellow}{val}{T.normal}')
    elif hasattr(args, 'func') and args.func:
        LOG.debug('RRRRRRUUUUNN FUNC  %s   WW', args.func)
        trio.run(args.func, args)


def enter():
    """Run sync for setuptools."""
    LOG.debug('WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW')
    sys.exit(tapedeck_cli())


if __name__ == '__main__':
    LOG.debug('XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX')
    enter()
