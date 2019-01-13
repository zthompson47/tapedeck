"""Test the pypeline subprocess control module."""
from pathlib import Path
import shlex

import trio

import tapedeck
from tapedeck import pypeline


def test_module_import():
    """Import the pypeline module."""
    assert pypeline


async def test_producer():
    """Run a process and read stdout."""
    command = 'python -m tapedeck.cli -v'
    config = {'COVERAGE_PROCESS_START': 'setup.cfg',
              'PYTHONPATH': str(Path('.').resolve()), }

    proc = pypeline.Producer(command, config)

    assert proc.cmd == shlex.split(command)
    assert proc.stat is None
    assert proc.proc is None
    for key in config:
        assert key in proc.env

    output = await proc.run_with_output()

    assert proc.stat == 0
    assert proc.proc.__class__ == trio.subprocess.Process
    assert output == tapedeck.__version__
    assert proc.read() == output
