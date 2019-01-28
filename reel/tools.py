"""Utility functions for the reel package."""
import trio

__all__ = ['resolve']


async def resolve(path):
    """Return the canonical str representation of the file path."""
    expanded = await trio.Path(path).expanduser()
    resolved = await expanded.resolve()
    return str(resolved)
