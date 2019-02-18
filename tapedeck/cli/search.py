"""The ``tapedeck`` cli 'search' command."""
import logging
import pathlib

import blessings
import trio

from reel.config import get_xdg_cache_dir

from tapedeck.search import find_tunes

LOG = logging.getLogger(__name__)
T = blessings.Terminal()


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
