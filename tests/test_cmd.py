"""Test the pre-configured commands."""
import os

from reel import cmd
from reel.cmd import ffmpeg, play


async def test_cmd_module():
    """Import the cmd module."""
    assert cmd
    assert cmd.SRC_SILENCE


async def test_play_radio():
    """Play a few seconds of music."""
    radio = 'http://ice1.somafm.com/groovesalad-256-mp3'
    music = ''.join(['https://archive.org/download/',
                     'gd1977-05-08.shure57.stevenson.29303.flac16/',
                     'gd1977-05-08d02t04.flac'])
    async with await play.speaker() as out:
        async with await ffmpeg.stream(music) as src:
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
        async with await ffmpeg.stream(radio) as src:
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
