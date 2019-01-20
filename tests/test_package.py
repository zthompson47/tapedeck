# pylint: disable=W0611, W0621
"""Test the reel subprocess control module."""
import os
from pathlib import Path

import trio

import reel
from reel.proc import LIMIT, Source
from tests.fixtures import audio_dir


async def test_version():
    """Run a process and read stdout."""
    src = Source('python   -m   reel.cli  -v')
    assert isinstance(src._command, list)  # pylint: disable=protected-access
    assert src.cmd == 'python -m reel.cli -v'
    assert src._env == os.environ  # pylint: disable=protected-access
    assert src.err == ''
    assert src._proc is None  # pylint: disable=protected-access
    assert src.status is None
    assert src._limit == LIMIT  # pylint: disable=protected-access
    assert src._nurse is None  # pylint: disable=protected-access

    version = await src.read_text()
    assert src.status == 0
    assert src.err == ''
    assert isinstance(src._proc,  # pylint: disable=protected-access
                      trio.subprocess.Process)
    assert version == reel.__version__


async def test_pwd():
    """Test a familiar shell command."""
    assert str(Path('.').resolve()) == await Source('pwd').read_text()


async def test_stderr():
    """Run a process and read stderr."""
    not_here = Source('ls /not_here_i_hope')
    assert not await not_here.read_text()  # no output
    assert not_here.status  # error present
    assert not_here.err  # some error about a missing file
    assert 'not_here' in not_here.err


async def test_limit_output():
    """Make sure streaming output from stdout & stderr is limited."""
    infinity = await Source('cat /dev/zero').read_text()
    assert len(infinity) >= LIMIT
    assert len(infinity) <= 2 * LIMIT


async def test_stdin():
    """Send some input to a command."""
    china = await Source('cat').read_text('sunflower')
    assert china == 'sunflower'


# async def test_source_stream():
#     """Process a big file of raw audio."""
#     cmd = '''ffmpeg -ac 2 -i xmas.flac
#              -f s16le -ar 44.1k -acodec pcm_s16le -'''
#     async with Source(cmd) as xmas:
#         async with await xmas.stream() as src:
#             assert isinstance(src, trio.abc.ReceiveStream)
#             size = 0
#             while True:
#                 chunk = await src.receive_some(16384)
#                 if not chunk:
#                     break
#                 size += len(chunk)
#             assert size == 57684912


async def test_short_context():
    """Run a short command with i / o in context managers."""
    async with await Source('cat').stream('china') as sun:
        assert isinstance(sun, reel.io.Output)
        assert len(await sun.read_bytes()) == 5


async def test_audio_dir(audio_dir):
    """Get test audio files."""
    assert audio_dir.exists()
    # assert (audio_dir / 'output.wav').exists()


# async def test_log_stderr():
#     """Read the messages sent from stderr."""
#     with trio.move_on_after(5):
#         cmd = '''ffmpeg -ac 2 -i http://ice1.somafm.com/groovesalad-256-mp3
#                  -f s16le -ar 44.1k -acodec pcm_s16le -'''
#         async with Source(cmd) as soma:
#             soma.log_err(
