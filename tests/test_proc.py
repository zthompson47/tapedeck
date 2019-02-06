"""Tests for :mod:`reel.proc`."""
import os

import trio

import reel

# pylint: disable=W0212


async def test_class_spool(capsys):
    """Run a process and read stdout."""
    src = reel.Spool('python   -m   reel.cli  -v')  # ... make separate tests
    assert isinstance(src._command, list)  # pylint: disable=protected-access
    assert src._env == os.environ  # pylint: disable=protected-access
    assert isinstance(src._proc, trio.Process)
    assert src._status is None
    assert src._limit is None

    version = await src.run()
    assert src.returncode == 0
    assert src.stderr == ''
    assert isinstance(src._proc,  # pylint: disable=protected-access
                      trio.Process)
    assert version == reel.__version__

    # not sure why here..  from another test, but test logging somwhere?
    captured = capsys.readouterr()
    assert captured.out == ''
    assert captured.err == ''


async def test_spool_simple_command():
    """Run a simple command with :class:`reel.Spool`."""

    # Use :func:`reel.Spool.run` to read the output of a command.
    china = await reel.Spool('cat').run('sunflower')
    assert china == 'sunflower'

    # Use :class:`reel.Transport` to read the output in a managed context.
    async with reel.Spool('cat') as china:
        assert await china.read('sunflower') == 'sunflower'


async def test_pwd():
    """Test a familiar shell command."""
    assert str(trio.Path.cwd()) == await reel.Spool('pwd').run()


async def test_limit_output():
    """Set a cutoff limit on output."""
    infinity = await reel.Spool('cat /dev/zero').limit(4747).run()
    assert len(infinity) >= 4747
    assert len(infinity) <= 4747 * 2


async def test_source_run_timeout():
    """Make sure a process returns normally with a timeout interrupt."""
    random = reel.Spool('cat /dev/random').timeout(0.47)
    garbage = await random.run(text=False)
    assert garbage and garbage != b''
    assert random.returncode <= 0


async def test_stderr():
    """Run a process and read stderr."""
    not_here = reel.Spool('ls /not_here_i_hope')
    assert not await not_here.run()  # no output
    # assert not_here.stderr  # some error about a missing file
    # assert not_here.returncode  # error present
    # assert 'not_here' in not_here.err


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


# async def test_log_stderr():
#     """Read the messages sent from stderr."""
#     with trio.move_on_after(5):
#         cmd = '''ffmpeg -ac 2 -i http://ice1.somafm.com/groovesalad-256-mp3
#                  -f s16le -ar 44.1k -acodec pcm_s16le -'''
#         async with Source(cmd) as soma:
#             soma.log_err(
