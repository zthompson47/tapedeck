"""Command line interface to :mod:`reel`."""
import argparse
import logging
import os
import sys

import pkg_resources
import trio

import reel

if 'REEL_LOG_LEVEL' in os.environ:
    LOG_DIR = trio.run(reel.config.get_xdg_data_dir, 'reel')
    LOG_FILE = LOG_DIR / 'cli.log'
    LOG_LEVEL = os.environ.get('REEL_LOG_LEVEL').upper()
    logging.basicConfig(filename=LOG_FILE, level=LOG_LEVEL)
LOGGER = logging.getLogger(__name__)
LOGGER.debug('Begin logging for reel <~-~-~(~<~(o~>)~)~-~-~>')


async def main() -> int:
    """Test."""
    await trio.sleep(0)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-c', '--config', action='store_true',
        help='print the configuration'
    )
    parser.add_argument(
        '-v', '--version', action='store_true',
        help='print the version'
    )
    args = parser.parse_args()
    if args.config:
        if 'REEL_LOG_LEVEL' in os.environ:
            print(f'REEL_LOG_DIR={LOG_DIR}')
            print(f'REEL_LOG_FILE={LOG_FILE}')
            print(f'REEL_LOG_LEVEL={LOG_LEVEL}')
    if args.version:
        print(pkg_resources.get_distribution('reel').version)

    return 0


def enter():
    """Run the main program as an ``entry_point`` for :mod:`setuptools`."""
    sys.exit(trio.run(main))


if __name__ == '__main__':
    enter()
