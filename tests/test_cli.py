"""Test suite for the tapedeck command line interface."""
from trio_click.testing import CliRunner

import tapedeck
from tapedeck import cli
from reel.proc import Source

ENV_COVERAGE = {'COVERAGE_PROCESS_START': 'setup.cfg', 'PYTHONPATH': '.'}


async def test_no_args():
    """Run tapedeck with no arguments."""
    runner = CliRunner()
    result = await runner.invoke(cli.main)
    assert result.exit_code == 0
    assert result.output == ''


async def test_version():
    """Show the version number."""
    runner = CliRunner()
    result = await runner.invoke(cli.main, ['--version'])
    assert result.exit_code == 0
    assert tapedeck.__version__ in result.output


async def test_no_args_external():
    """Run the CLI externally with no arguments."""
    noargs = Source('python -m tapedeck.cli', ENV_COVERAGE)
    output = await noargs.run()
    assert noargs.status == 0
    assert output == ''


async def test_version_external():
    """Show the version number by running the actual CLI."""
    version = Source('python -m tapedeck.cli -v', ENV_COVERAGE)
    output = await version.read_text()
    assert version.status == 0
    assert output == tapedeck.__version__
