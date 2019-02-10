"""Test the API."""
import logging

import trio

import reel
from reel import Spool
from reel.config import get_config, get_xdg_config_dir

LOG = logging.getLogger(__name__)


async def test_shell_commands():
    """Run a few shell commands."""
    assert 'rutabaga' in await Spool(f'grep utabag {__file__}').run()

    async with Spool('find .', xflags=['-type', 'f']) as found:
        lines = await found.readlines()
        found_resolved = [await reel.Path.canon(_) for _ in lines]
        assert __file__ in found_resolved

    assert float((await Spool('python -V').run())[7:10]) >= 3.5

    xconf = ['-c', "import os; print(os.environ['_ASDF'])"]
    env = {'_ASDF': 'asdf'}
    assert await Spool('python', xflags=xconf, xenv=env).run() == 'asdf'

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
    LOG.debug(']]]]]]]]]]]]]]]]]]]]] config dir: %s', config_dir)
    # ... get_config needs better naming, e.g. get_config_from_template
    config = await get_config(config_dir, 'icecast.xml', **config_icecast)
    LOG.debug(']]]]]]]]]]]]]]]]]]]]] config: %s', str(config))
    flags = ['-c', str(config)]

    # Start an icecast daemon.
    async with Spool('icecast', xflags=flags) as icecast:
        async with trio.open_nursery() as nursery:
            icecast.start_daemon(nursery)

            await trio.sleep(0.5)  # give icecast time to start

            # Make sure it started.
            async with Spool('ps ax') | Spool('grep icecast') as procs:
                found_it = False
                lines = await procs.readlines()
                for line in lines:
                    if str(config) in line:
                        found_it = True
                # ... WEIRD!! 'assert False' here hangs!!!!!
                assert found_it
            await icecast.stop()

    # Check the process list for no zombies.
    async with Spool('ps ax') as proclist:
        found = False
        for line in await proclist.readlines():
            if str(config) in line:
                found = True
        assert not found
