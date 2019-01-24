# pylint: disable=W0611, W0621
"""Test the pre-configured commands."""
import os

from reel import cmd
from reel.cmd import (
    ffmpeg, sox, tapedeck
)
from reel.io import StreamIO

from tests.fixtures import music_dir, RADIO, SONG

BYTE_LIMIT = 1000000


async def test_cmd_module():
    """Import the cmd module."""
    assert cmd
    assert cmd.SRC_SILENCE


async def test_play_music(capsys):
    """Play a few seconds of music."""
    async with await sox.play() as out:
        async with await ffmpeg.stream(SONG) as src:
            count = 0
            chunk = await src.receive_some(4096)
            while chunk:
                if os.environ.get('REEL_ALLOW_AUDIO_PLAY'):
                    await out.send_all(chunk)
                if count > 200:
                    break
                chunk = await src.receive_some(4096)
                count += 1
                assert chunk
        async with await ffmpeg.stream(RADIO) as src:
            count = 0
            chunk = await src.receive_some(4096)
            while chunk:
                if os.environ.get('REEL_ALLOW_AUDIO_PLAY'):
                    await out.send_all(chunk)
                if count > 200:
                    break
                chunk = await src.receive_some(4096)
                count += 1
                assert chunk

    # put these somewhere better - "check output doesn't bork ipython"
    captured = capsys.readouterr()
    assert captured.out == ''
    assert captured.err == ''


async def test_play_music_better_way():
    """Play a few seconds of music with less code."""
    if os.environ.get('REEL_ALLOW_AUDIO_PLAY'):
        async with await sox.play() as out:
            async with await ffmpeg.stream(SONG) as src:
                await StreamIO(src, out).flow(byte_limit=1000000)
            async with await ffmpeg.stream(RADIO) as src:
                await StreamIO(src, out).flow(byte_limit=1000000)


async def test_cmd_tapedeck(music_dir):
    """Run tapedeck.cli through reel.cmd."""
    results = await tapedeck.search(music_dir)
    assert len(results) == 3
