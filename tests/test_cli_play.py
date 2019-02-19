"""Tests for the 'tapedeck play' cli command."""
import logging
import shlex

import trio

import reel
from reel import Spool

import tapedeck

LOG_FILE = trio.run(tapedeck.config.logfile, 'tests.log')
logging.basicConfig(filename=LOG_FILE, level='DEBUG')
LOG = logging.getLogger(__name__)
LOG.debug('Begin logging for test_cli_play ((o))')


async def test_play(env_audio_dest):
    """Stream from source to destination."""
    audio_uri = '/Users/zach/out000.wav'
    player = reel.Spool(
        f'python -m tapedeck.cli.main play {audio_uri} -o {env_audio_dest}'
    )
    # await player.run(timeout=4.7)  # ... needs clean kill
    await player.timeout(4.7).run()
    assert player.returncode <= 0  # ... maybe it should not be an erorr?


async def test_tdplay(audio_uris, env_audio_dest):
    """Stream some audio to nowhere with ``tdplay``."""
    audio_clip = Spool(f"tdplay {audio_uris['wav0']} -o {env_audio_dest}")
    await audio_clip.run()
    assert audio_clip.returncode <= 0


async def test_play_directory(env_audio_dest):
    """Detect a directory and play each song."""
    directory = shlex.quote(
        '/Users/zach/tunes/1972 - #1 Record [2009 Remaster]'
    )  # ... test more with quoting and bad characters in filenames ...
    player = reel.Spool(
        f'python -m tapedeck.cli.main play {directory} -o {env_audio_dest}'
    )
    await player.timeout(20).run()
    LOG.debug("error: %s", player.stderr)

    # Either finishes cleanly or times out.
    assert player.returncode == 0 or player.returncode == -9

    # ... need to test sort ...
    # weird how pytest will x-pass even with undefined vars etc


async def test_play_shuffle():
    """Shuffle a playlist."""


async def test_play_loop():
    """Repeat a playlist forever."""


async def test_host_port_env_config():
    """Use default host and port from environment variables."""
    audio_uri = '/Users/zach/out000.wav'

    # Try with no host or port.
    player = reel.Spool(f'tapedeck play {audio_uri} -o udp')
    await player.run()
    assert player.returncode > 0
    # assert 'udp needs host and port' in player.err  # ... CAN'T GET STDERR

    # Set a host and port.
    x_env = {'TAPEDECK_UDP_HOST': '127.0.0.1', 'TAPEDECK_UDP_PORT': '9876'}
    player = reel.Spool(f'tapedeck play {audio_uri} -o udp', x_env)
    # await player.run()
    # assert player.status <= 0
