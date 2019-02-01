"""Test suite for the tapedeck command line interface."""
import os

import pytest
from trio_click.testing import CliRunner

from reel import cmd
from reel.proc import Source
from reel.tools import resolve

import tapedeck

# ??? to get runner.invoke to find the cli entry:
import tapedeck.cli
import tapedeck.cli.main
# ???

CMD = CliRunner()


async def test_no_args():
    """Run tapedeck with no arguments."""
    result = await CMD.invoke(tapedeck.cli.main.tapedeck_cli)
    assert result.exit_code == 0
    assert result.output == ''


async def test_version():
    """Show the version number."""
    result = await CMD.invoke(tapedeck.cli.main.tapedeck_cli, ['--version'])
    assert result.exit_code == 0
    assert tapedeck.__version__ in result.output


async def test_version_with_dist():
    """Show the version number with the distributed executable."""
    dist = Source('tapedeck --version')
    version = await dist.read_text()
    assert dist.status == 0
    assert tapedeck.__version__ in version


async def test_no_args_external():
    """Run the CLI externally with no arguments."""
    noargs = Source('python -m tapedeck.cli.main')
    output = await noargs.run()
    assert noargs.status == 0
    assert output == ''


async def test_version_external():
    """Show the version number by running the actual CLI."""
    version = Source('python -m tapedeck.cli.main --version')
    output = await version.read_text()
    assert version.status == 0
    assert tapedeck.__version__ in output
