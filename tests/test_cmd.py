"""Test the pre-configured commands."""
import os

import trio

from reel import cmd
from reel.cmd import ffmpeg, play


async def test_cmd_module():
    """Import the cmd module."""
    assert cmd
    assert cmd.SRC_SILENCE


async def test_play_radio():
    """Play a few seconds of Groove Salad."""
    radio = 'http://ice1.somafm.com/groovesalad-256-mp3'
    with trio.move_on_after(5):
        async with await ffmpeg.stream(radio) as src:
            async with await play.speaker() as out:
                chunk = await src.receive_some(4096)
                while chunk:

                    if os.environ.get('REEL_ALLOW_AUDIO_PLAY'):
                        await out.send_all(chunk)

                    chunk = await src.receive_some(4096)
                    assert chunk
