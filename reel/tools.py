"""Utility functions for the reel package."""
from trio import Path

__all__ = ['resolve']


async def resolve(path):
    """Return the canonical str representation of the file path."""
    expanded = await Path(path).expanduser()
    resolved = await expanded.resolve()
    return str(resolved)

# def grep
