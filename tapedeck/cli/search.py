"""The ``tapedeck`` cli 'search' command."""
import logging
import pathlib

import blessings
import trio
import trio_click as click

from reel.config import get_xdg_cache_dir

from tapedeck.search import find_tunes

T = blessings.Terminal()


@click.command(options_metavar='[options]', help='¤ Search For Music')
@click.argument('directory', metavar='[directory]', required=False)
@click.option('-d', '--follow-dots', is_flag=True,
              help='Search hidden dot-directories.')
@click.option('-l', '--follow-links', is_flag=True,
              help='Search symlinked directories.')
@click.option('-m', '--memory', is_flag=True,
              help='Show last search from memory')
async def search(directory, follow_links, follow_dots, memory):
    """Search for music."""
    click.echo('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!', err=True)
    if memory:
        # Read the cached search file.
        cache_file = await get_xdg_cache_dir('tapedeck') / 'search.txt'
        async with await cache_file.open('r') as out:
            lines = (await out.read()).split('\n')[0:-1]
        logging.debug(lines)

        # Print the cached search to a pager.
        output = []
        for line in lines:
            #  Convert absolute paths to folder names.
            index = line[0:line.find(' ')]  # e.g. '1. '
            filename = line[line.find(' ') + 1:]  # e.g. '/full/path'
            path = trio.Path(filename)
            output.append(f'{T.green}{index} {T.blue}{path.name}{T.normal}')
        click.echo_via_pager('\n'.join(output))
        return

    results = await find_tunes(
        directory,
        followlinks=follow_links,
        followdots=follow_dots
    )
    # Sort search results by lowercase folder name.
    results.sort(key=lambda _: pathlib.Path(_.path).name.lower())

    idx = 0
    for folder in results:
        idx += 1
        path = trio.Path(folder.path)
        click.echo(f'  {T.green}{idx}. {T.blue}{path.name}{T.normal}')

    # Store results in a cache file.
    cache_file = await get_xdg_cache_dir('tapedeck') / 'search.txt'
    async with await cache_file.open('w') as out:
        idx = 0
        # Sort alphabetically, case insensitive. ... test needed ...
        for folder in results:
            idx += 1
            await out.write(f'{idx}. {str(folder.path)}\n')
