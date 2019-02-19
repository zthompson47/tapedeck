"""Test suite for the tapedeck command line interface."""
from reel import Spool

import tapedeck

# ??? to get runner.invoke to find the cli entry:
import tapedeck.cli
import tapedeck.cli.main
# ???


async def test_version_with_dist():
    """Show the version number with the distributed executable."""
    dist = Spool('tapedeck --version')
    version = await dist.run()
    assert dist.returncode == 0
    assert tapedeck.__version__ in version


async def test_no_args_external():
    """Run the CLI externally with no arguments."""
    noargs = Spool('python -m tapedeck.cli.main')
    output = await noargs.run()
    assert noargs.returncode == 0
    assert output is None


async def test_version_external():
    """Show the version number by running the actual CLI."""
    version = Spool('python -m tapedeck.cli.main --version')
    output = await version.run()
    assert version.returncode == 0
    assert tapedeck.__version__ in output


async def test_subcommand_executables():
    """Make sure the various executables can run."""
    commands = [
        'tapedeck -v', 'python -m tapedeck.cli.main -v',
        'tapedeck -c', 'python -m tapedeck.cli.main -c',
        'tapedeck play -h', 'python -m tapedeck.cli.play -h',
        'tapedeck search -h', 'python -m tapedeck.cli.search -h',
        'tdplay -h', 'tdsearch -h',
        'python tapedeck/cli/main.py -h',
        'python tapedeck/cli/search.py -h',
        'python tapedeck/cli/play.py -h',
    ]
    for command in commands:
        exe = Spool(command)
        output = await exe.run()
        assert exe.returncode == 0  # successful exit
        assert len(output) > 3  # they all print something to stdout
