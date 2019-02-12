"""Test suite for the tapedeck command line interface."""
from trio_click.testing import CliRunner

import reel

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
    dist = reel.Spool('tapedeck --version')
    version = await dist.run()
    assert dist.returncode == 0
    assert tapedeck.__version__ in version


async def test_no_args_external():
    """Run the CLI externally with no arguments."""
    noargs = reel.Spool('python -m tapedeck.cli.main')
    output = await noargs.run()
    assert noargs.returncode == 0
    assert output is None


async def test_version_external():
    """Show the version number by running the actual CLI."""
    version = reel.Spool('python -m tapedeck.cli.main --version')
    output = await version.run()
    assert version.returncode == 0
    assert tapedeck.__version__ in output
