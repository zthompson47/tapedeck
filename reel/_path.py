"""A wrapper for ``pathlib.Path`` and ``trio.Path``.

``pathlib.Path`` is not async, ``trio.Path`` has(d?) a bug with
``trio.Path.home``, and ``reel`` can use some extra methods in this
useful class.

"""
import pathlib

import trio


class Path(trio.Path, str):
    """A path object with some added file streaming methods."""

    @classmethod
    def home(cls):
        """Return $HOME."""
        return pathlib.Path.home()

    @classmethod
    async def canon(cls, path):
        """Return the canonical string representation of a file path."""
        expanded = await trio.Path(path).expanduser()
        resolved = await expanded.resolve()
        return str(resolved)
