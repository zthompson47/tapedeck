"""Test the reel utility functions."""
import pathlib  # trio.Path.home() gives error

import trio

import reel.tools


def test_import():
    """Import the utility functions."""
    assert reel.tools


async def test_resolve():
    """Resolve file paths to canonical form as a str."""
    assert await reel.tools.resolve('.') == str(trio.Path().cwd())
    assert await reel.tools.resolve('~') == str(pathlib.Path.home())

    parent = await reel.tools.resolve('../')
    assert parent == str(await trio.Path('..').resolve())
    assert parent == str((await trio.Path('.').resolve()).parent)
