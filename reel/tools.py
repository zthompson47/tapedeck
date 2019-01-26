"""Utility functions for the reel package."""
import ansicolortags

import trio
from trio import Path
import trio_click as click

__all__ = ['resolve']


async def resolve(path):
    """Return the canonical str representation of the file path."""
    expanded = await Path(path).expanduser()
    resolved = await expanded.resolve()
    return str(resolved)


async def click_echof(string):
    """Format a string with colors and variables and send to ``click.echo``."""
    await trio.run_sync_in_worker_thread(
        click.echo,
        ansicolortags.sprint(string)
    )
