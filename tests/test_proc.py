"""Tests for :mod:`reel.proc`."""
import trio

import reel


async def test_class_spool(capsys):
    """Run a process and read stdout."""
    src = reel.Spool('python   -m   reel.cli  -v')  # ... make separate tests
    version = await src.run()
    assert src.returncode == 0
    assert src.stderr is None
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
    assert not_here.stderr  # some error about a missing file
    assert not_here.returncode  # error present
    assert 'not_here' in not_here.stderr
