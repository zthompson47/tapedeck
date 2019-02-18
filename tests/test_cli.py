"""Test suite for the tapedeck command line interface."""
import reel

import tapedeck

# ??? to get runner.invoke to find the cli entry:
import tapedeck.cli
import tapedeck.cli.main
# ???


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
