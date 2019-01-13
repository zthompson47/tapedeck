"""Test suite for the tapedeck command line interface."""
import os

from trio import subprocess
from trio_click.testing import CliRunner

import tapedeck
from tapedeck import cli


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
    new_env = os.environ
    new_env['COVERAGE_PROCESS_START'] = '.coveragerc'
    new_env['PYTHONPATH'] = '.'
    td_proc = subprocess.Process(
        ['python', '-m', 'tapedeck.cli', '-v'],
        stdout=subprocess.PIPE,
        env=new_env
    )
    result = b''
    async with td_proc:
        await td_proc.wait()
        assert td_proc.returncode == 0

        # Put output stream into one string
        async with td_proc.stdout as out:
            some = await out.receive_some(8)
            while some:
                result += some
                some = await out.receive_some(8)

    assert result.decode('utf-8').strip() == tapedeck.__version__


async def test_no_args_external():
    """Run the CLI externally with no arguments."""
    new_env = os.environ
    new_env['COVERAGE_PROCESS_START'] = '.coveragerc'
    new_env['PYTHONPATH'] = '.'
    td_proc = subprocess.Process(
        ['python', '-m', 'tapedeck.cli'],
        stdout=subprocess.PIPE,
        env=new_env
    )
    result = b''
    async with td_proc:
        await td_proc.wait()
        assert td_proc.returncode == 0

        # Put output stream into one string
        async with td_proc.stdout as out:
            some = await out.receive_some(8)
            while some:
                result += some
                some = await out.receive_some(8)

    assert result.decode('utf-8').strip() == ''
