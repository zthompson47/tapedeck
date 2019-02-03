"""Test the reel utility functions."""
import pathlib  # trio.Path.home() gives error

import pytest
import trio

from reel import Path


async def test_resolve():
    """Resolve file paths to canonical form as a str."""
    assert await Path.canon('.') == str(trio.Path.cwd())
    assert await Path.canon('~') == str(pathlib.Path.home())

    parent = await Path.canon('../')
    assert parent == str(await trio.Path('..').resolve())
    assert parent == str((await trio.Path('.').resolve()).parent)

    assert await Path.canon('.') == str(trio.Path.cwd())


async def test_path():
    """Wrap trio.Path and pathlib.Path into one, with extra stuff."""
    r_path_home = Path('~')
    t_path_home = trio.Path('~')
    p_path_home = pathlib.Path('~')

    # reel.Path is a str.
    assert isinstance(r_path_home, str)
    assert not isinstance(t_path_home, str)
    assert not isinstance(p_path_home, str)

    # Check that all home dirs look the same.
    assert r_path_home == t_path_home == p_path_home

    # trio.Path.home is currently broken.
    assert isinstance(r_path_home, trio.Path)
    assert Path.home() == pathlib.Path.home()  # reel.Path.home works
    assert await r_path_home.expanduser() == pathlib.Path.home()
    with pytest.raises(AttributeError):
        trio.Path.home()
