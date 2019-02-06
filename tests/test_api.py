# pylint: disable=W0401, W0611, W0614, W0621
"""Test the API."""
import reel
from reel.config import (
    get_config,
    get_xdg_config_dir,
)
from reel.cmd import *
from reel.io import *
from reel.proc import *


async def test_shell_commands():
    """Run a few shell commands."""
    assert 'rutabaga' in await reel.Spool(f'grep utabag {__file__}').run()

    async with reel.Spool('find .', xflags=['-type', 'f']) as found:
        lines = await found.readlines()
        found_resolved = [await reel.Path.canon(_) for _ in lines]
        assert __file__ in found_resolved

    assert float((await reel.Spool('python -V').run())[7:10]) >= 3.5

    xconf = ['-c', "import os; print(os.environ['_ASDF'])"]
    env = {'_ASDF': 'asdf'}
    assert await reel.Spool('python', xflags=xconf, xenv=env).run() == 'asdf'

    # fname = 'test.flac'
    # assert await Source(f'flac -t {fname}').read_bool()
    # assert isinstance(await Source(f'flac -t {fname}').read_bool(), bool)

    # async with Source(f'flac -t {fname}') as test:
    #     assert await test.read_bool()
    #     assert test.status == 0
    #     assert 'test.flac: ok' in test.err

    # wav = await Source(f'flac -cd {fname}').read_bytes()
    # assert len(wav) == 57684956
    # flac = await Source(f'flac -c -').read_bytes(send_bytes=wav)
    # assert len(flac) == 27583002


async def test_server(config_icecast):
    """Run a server."""
    config_dir = await get_xdg_config_dir()
    # ... get_config needs better naming, e.g. get_config_from_template
    config = await get_config(config_dir, 'icecast.xml', **config_icecast)
    xconf = ['-c', str(config)]
    async with Daemon('icecast', xconf=xconf) as icecast:
        await icecast.start()
        async with reel.Spool('ps ax') as procs:
            found = False
            for proc in await procs.readlines():
                if 'icecast' in proc:
                    found = True
            assert found
    async with reel.Spool('ps ax') as procs:
        found = False
        for proc in await procs.readlines():
            if 'icecast' in proc:
                found = True
        assert not found
