"""Test suite for the reel command line interface."""
from trio_click.testing import CliRunner

import reel
from reel import cli
from reel.proc import Source


async def test_no_args():
    """Run cli with no arguments."""
    runner = CliRunner()
    result = await runner.invoke(cli.main)
    assert result.exit_code == 0
    assert result.output == ''


async def test_version():
    """Show the version number."""
    runner = CliRunner()
    result = await runner.invoke(cli.main, ['--version'])
    assert result.exit_code == 0
    assert reel.__version__ in result.output


async def test_no_args_external():
    """Run the CLI externally with no arguments."""
    command = 'python -m reel.cli'
    noargs = Source(command)
    output = await noargs.run()
    assert noargs.status == 0
    assert output == ''


async def test_version_external():
    """Show the version number by running the actual CLI."""
    command = 'python -m reel.cli -v'
    version = Source(command)
    output = await version.read_text()
    assert version.status == 0
    assert output == reel.__version__


async def test_dump_config():
    """Show the current configuration."""
    command = 'python -m reel.cli --config'
    config = Source(command)
    dump = await config.read_list()
    assert len(dump) == 3
    assert config.status == 0
    for line in dump:
        assert line.startswith('REEL_')
