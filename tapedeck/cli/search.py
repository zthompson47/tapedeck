"""The ``tapedeck`` cli 'search' command."""
import argparse
import logging
import pathlib
import sys

import blessings
import trio

from reel.config import get_xdg_cache_dir

from tapedeck.search import find_tunes

LOG = logging.getLogger(__name__)
T = blessings.Terminal()


def load_args(tdsearch):
    """Parse the args."""
    # o=~ tdsearch ~=o
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
    tdsearch.set_defaults(func=search)


async def search(args):
    """Search for music."""
    if args.memory:
        # Read the cached search file.
        cache_file = await get_xdg_cache_dir('tapedeck') / 'search.txt'
        async with await cache_file.open('r') as out:
            lines = (await out.read()).split('\n')[0:-1]
        LOG.debug(lines)

        # Print the cached search to a pager.
        output = []
        for line in lines:
            #  Convert absolute paths to folder names.
            index = line[0:line.find(' ')]  # e.g. '1. '
            filename = line[line.find(' ') + 1:]  # e.g. '/full/path'
            path = trio.Path(filename)
            output.append(f'{T.green}{index} {T.blue}{path.name}{T.normal}')
        print('\n'.join(output))
        return

    results = await find_tunes(
        args.directory,
        followlinks=args.follow_links,
        followdots=args.follow_dots
    )

    # Sort search results by lowercase folder name.
    results.sort(key=lambda _: pathlib.Path(_.path).name.lower())

    idx = 0
    for folder in results:
        idx += 1
        path = trio.Path(folder.path)
        print(f'  {T.green}{idx}. {T.blue}{path.name}{T.normal}')

    # Store results in a cache file.
    cache_file = await get_xdg_cache_dir('tapedeck') / 'search.txt'
    async with await cache_file.open('w') as out:
        idx = 0

        # Sort alphabetically, case insensitive. ... test needed ...
        for folder in results:
            idx += 1
            await out.write(f'{idx}. {str(folder.path)}\n')

    return 0


def enter():
    """Entry point for setuptools console_scripts."""
    tdsearch = argparse.ArgumentParser()
    load_args(tdsearch)
    args = tdsearch.parse_args()
    sys.exit(trio.run(search, args))


if __name__ == '__main__':
    enter()
