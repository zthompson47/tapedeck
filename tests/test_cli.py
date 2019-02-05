"""Test suite for the :mod:`reel.cli` command line interface."""
import reel
from reel.proc import Source


async def test_no_args(cli_cmd):
    """Run :mod:`reel.cli` with no arguments."""
    noargs = Source(cli_cmd)
    output = await noargs.run()
    assert noargs.status == 0
    assert output == ''


async def test_version(cli_cmd):
    """Show the version number."""
    for flag in ['-v', '--version']:
        command = f'{cli_cmd} {flag}'
        version = Source(command)
        output = await version.read_text()
        assert version.status == 0
        assert output == reel.__version__


async def test_config(cli_cmd):
    """Show the current configuration."""
    for flag in ['-c', '--config']:
        command = f'{cli_cmd} {flag}'
        config = Source(command)
        dump = await config.read_list()
        assert len(dump) == 3
        assert config.status == 0
        for line in dump:
            assert line.startswith('REEL_')
