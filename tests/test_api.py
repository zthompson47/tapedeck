"""Test the API."""
import logging

import trio
from trio import Path

from reel import Daemon, Server, Spool
from reel.config import get_config, get_xdg_config_dir

logging.basicConfig(
    filename='/Users/zach/asdf.log',
    level='DEBUG',
    format='%(levelname)s:%(lineno)d:%(module)s:%(funcName)s:%(message)s'
)
LOG = logging.getLogger(__name__)


async def test_shell_commands():
    """Run a few shell commands."""
    assert 'rutabaga' in await Spool(f'grep utabag {__file__}').run()

    async with Spool('find .', xflags=['-type', 'f']) as found:
        lines = await found.readlines()
        found_resolved = [str(await Path(_).resolve()) for _ in lines]
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
    config = await get_config(config_dir, 'icecast.xml', **config_icecast)
    flags = ['-c', str(config)]

    # Start an icecast daemon.
    LOG.debug('------>><<>><< before open_nursery')
    async with trio.open_nursery() as nursery:
        LOG.debug('------>><<>><< before async with daemon')
        async with Daemon('icecast', xflags=flags) > nursery as icecast:
            LOG.debug('------>><<>><< after async with daemon')
            assert isinstance(icecast, Server)
            # nursery.start_soon(icecast.run, nursery)
            # icecast.start_daemon(nursery)

            await trio.sleep(0.5)  # give icecast time to start

            # Make sure it started.
            async with Spool('ps ax') | Spool('grep icecast') as procs:
                LOG.debug('------>><<>><< after async with spool')
                found_it = False
                lines = await procs.readlines()
                LOG.debug('------>><<>><< BEFORE lines')
                for line in lines:
                    LOG.debug('------>><<>><< IN lines')
                    if str(config) in line:
                        found_it = True
                # ... WEIRD!! 'assert False' here hangs!!!!!
                assert found_it
            # await icecast.stop()
            LOG.debug('------>><<>><< OUT of spool')
        LOG.debug('------>><<>><< OUT of daemon')
    LOG.debug('------>><<>><< OUT of nursery')

    # Check the process list for no zombies.
    async with Spool('ps ax') as proclist:
        found = False
        for line in await proclist.readlines():
            if str(config) in line:
                found = True
        assert not found
