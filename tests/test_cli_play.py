"""Tests for the 'tapedeck play' cli command."""
import shlex

import pytest

from reel.proc import Source

from tests.fixtures import RADIO, env_audio_dest, music_dir


async def test_play(env_audio_dest):
    """Stream from source to destination."""
    print(env_audio_dest)
    player = Source(
        f'python -m tapedeck.cli.main play {RADIO} -o {env_audio_dest}'
    )
    await player.run(timeout=4.7)
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
