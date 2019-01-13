"""Test suite for the tapedeck command line interface."""
from pathlib import Path

from trio_click.testing import CliRunner

import tapedeck
from tapedeck import cli
from tapedeck import pypeline


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


async def test_version_external():
    """Show the version number by running the actual CLI."""
    command = 'python -m tapedeck.cli -v'
    config = {'COVERAGE_PROCESS_START': 'setup.cfg',
              'PYTHONPATH': str(Path('.').resolve()), }
    proc = pypeline.Producer(command, config)
    output = await proc.run_with_output()
    assert proc.stat == 0
    assert output == tapedeck.__version__


async def test_no_args_external():
    """Run the CLI externally with no arguments."""
    command = 'python -m tapedeck.cli'
    config = {'COVERAGE_PROCESS_START': 'setup.cfg',
              'PYTHONPATH': str(Path('.').resolve()), }
    proc = pypeline.Producer(command, config)
    output = await proc.run_with_output()
    assert proc.stat == 0
    assert output == ''
