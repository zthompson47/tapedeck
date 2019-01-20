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
    config = {'COVERAGE_PROCESS_START': 'setup.cfg', 'PYTHONPATH': '.'}
    noargs = Source(command, config)
    output = await noargs.run()
    assert noargs.status == 0
    assert output == ''


async def test_version_external():
    """Show the version number by running the actual CLI."""
    command = 'python -m reel.cli -v'
    env = {'COVERAGE_PROCESS_START': 'setup.cfg', 'PYTHONPATH': '.'}
    version = Source(command, env)
    output = await version.read_text()
    assert version.status == 0
    assert output == reel.__version__
