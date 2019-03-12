"""Tests for :mod:`reel.proc`."""
from trio import move_on_after, Path

from reel import __version__, Spool


async def test_class_spool(capsys):
    """Run a process and read stdout."""
    src = Spool('python   -m   reel.cli  -v')  # ... make separate tests
    version = await src.run()
    assert src.returncode == 0
    assert src.stderr is None
    assert version == __version__

    # not sure why here..  from another test, but test logging somwhere?
    captured = capsys.readouterr()
    assert captured.out == ''
    assert captured.err == ''


async def test_spool_simple_command():
    """Run a simple command with :class:`reel.Spool`."""

    # Use :func:`Spool.run` to read the output of a command.
    china = await Spool('cat').run('sunflower')
    assert china == 'sunflower'

    # Use :class:`reel.Transport` to read the output in a managed context.
    async with Spool('cat') as china:
        assert await china.read('sunflower') == 'sunflower'


async def test_pwd():
    """Test a familiar shell command."""
    assert str(await Path.cwd()) == await Spool('pwd').run()


async def test_limit_output():
    """Set a cutoff limit on output."""
    infinity = Spool('cat /dev/zero').limit(47)
    order = len(await infinity.run())
    assert order == 47


async def test_source_run_timeout():
    """Make sure a process returns normally with a timeout interrupt."""
    random = Spool('cat /dev/random')
    with move_on_after(0.47):
        await random.run()
    assert random.stdout and random.stdout != b''
    # ??? cant get return value from run() on timeout
    # ??? is the process still running when we wait?
    # await random._proc.wait()
    # assert random.returncode <= 0


async def test_stderr():
    """Run a process and read stderr."""
    not_here = Spool('ls /not_here_i_hope')
    assert not await not_here.run()  # no output
    assert not_here.stderr  # some error about a missing file
    assert not_here.returncode  # error present
    assert 'not_here' in not_here.stderr
