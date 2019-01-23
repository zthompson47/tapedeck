"""Test the pre-configured commands."""
import os

from reel import cmd
from reel.cmd import ffmpeg, sox
from reel.io import StreamIO

BYTE_LIMIT = 1000000
RADIO = 'http://ice1.somafm.com/groovesalad-256-mp3'
SONG = ''.join(['https://archive.org/download/',
                'gd1977-05-08.shure57.stevenson.29303.flac16/',
                'gd1977-05-08d02t04.flac'])


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
    async with await sox.play() as out:
        async with await ffmpeg.stream(SONG) as src:
            await StreamIO(src, out).flow(byte_limit=1000000)
        async with await ffmpeg.stream(RADIO) as src:
            await StreamIO(src, out).flow(byte_limit=1000000)
