"""Tests for the 'tapedeck play' cli command."""
import os
import shlex

import pytest

from reel.proc import Source


async def test_play(env_audio_dest, uri):
    """Stream from source to destination."""
    audio_uri = '/Users/zach/out000.wav'
    player = Source(
        f'python -m tapedeck.cli.main play {audio_uri} -o {env_audio_dest}'
    )
    # await player.run(timeout=4.7)  # ... needs clean kill
    await player.run()
    assert player.status <= 0  # ... maybe it should not be an erorr?


async def test_play_directory(env_audio_dest):
    """Detect a directory and play each song."""
    directory = shlex.quote(
        '/Users/zach/tunes/1972 - #1 Record [2009 Remaster]'
    )  # ... test more ...
    player = Source(f'''python -m tapedeck.cli.main
                        play {directory}
                        -o {env_audio_dest}''')
    await player.run(timeout=4.7)
    assert player.status <= 0  # ... maybe it should not be an erorr? ...
    # ... need to test sort ...


async def test_play_shuffle(music_dir):
    """Shuffle a playlist."""


async def test_play_loop(music_dir):
    """Repeat a playlist forever."""


async def test_host_port_env_config():
    """Use default host and port from environment variables."""
    audio_uri = '/Users/zach/out000.wav'

    # Try with no host or port.
    player = Source(f'tapedeck play {audio_uri} -o udp')
    await player.run()
    assert player.status > 0
    # assert 'udp needs host and port' in player.err  # ... CAN'T GET STDERR

    # Set a host and port.
    x_env = {'TAPEDECK_UDP_HOST': '0.0.0.0', 'TAPEDECK_UDP_PORT': '9876'}
    player = Source(f'tapedeck play {audio_uri} -o udp', x_env)
    # await player.run()
    # assert player.status <= 0
