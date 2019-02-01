# pylint: disable=W0401, W0611, W0614, W0621
"""Test the API."""
import reel
from reel import (
    get_config,
    get_xdg_config_dir,
)
from reel.cmd import *
from reel.io import *
from reel.proc import *

from tests.fixtures import *


def test_import():
    """Import the reel module."""
    assert reel
    assert set(reel.__all__) >= set([
        'cmd', 'io', 'proc',
        'Path',
    ])
    # pylint: disable=protected-access
    assert set(reel._config.__all__) >= set([
        'get_config',
        'get_package_dir', 'get_package_name',
        'get_xdg_home', 'get_xdg_config_dir',
        'get_config', 'get_xdg_cache_dir',
    ])
    assert reel.cmd.__all__ == ['ffmpeg', 'sox']
    assert reel.io.__all__ == ['InputStream', 'OutputStream', 'StreamIO']
    assert reel.proc.__all__ == ['Daemon', 'Destination', 'ProcBase', 'Source']


async def test_shell_commands():
    """Run a few shell commands."""
    assert 'rutabaga' in await Source(f'grep utabag {__file__}').read_text()

    found = Source('find .', xconf=['-type', 'f'])
    assert __file__ in await found.read_list(through=reel.Path.canon)

    assert float((await Source('python -V').read_text())[7:10]) >= 3.5

    xconf = ['-c', "import os; print(os.environ['_ASDF'])"]
    env = {'_ASDF': 'asdf'}
    assert await Source('python', xconf=xconf, xenv=env).read_text() == 'asdf'

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
        procs = await Source('ps ax').read_list()
        found = False
        for proc in procs:
            if 'icecast' in proc:
                found = True
        assert found
    procs = await Source('ps ax').read_list()
    found = False
    for proc in procs:
        if 'icecast' in proc:
            found = True
    assert not found
