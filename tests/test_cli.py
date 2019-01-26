# pylint: disable=W0611,W0621
"""Test suite for the tapedeck command line interface."""
import os

import pytest
from trio_click.testing import CliRunner

from reel import cmd
from reel.proc import Source  # pylint: disable=C0411
from reel.tools import resolve

import tapedeck
from tapedeck import cli

from tests.fixtures import env_audio_dest, music_dir, ENV_COVERAGE, RADIO


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


async def test_just_do_something(env_audio_dest):
    """Make sure this thing can play some music."""
    music = Source(
        f'python -m tapedeck.cli --cornell 77 -o {env_audio_dest}',
        ENV_COVERAGE
    )
    await music.run(timeout=4.9)
    assert music.status <= 0


async def test_search(music_dir):
    """Find some music."""
    search = Source(f'python -m tapedeck.cli search {str(music_dir)}')
    # ... import coverage in default pyenv needed
    results = await search.read_list(through=resolve)
    assert search.status == 0
    assert len(results) == 3
    found = False
    for path in results:
        if path.endswith('subsubsubdir'):
            found = True
    assert found
    # ... hide dot files
    # ... hide symlinks


async def test_search_cache(music_dir):
    """Save each search and play folders by search index."""
    search = await cmd.tapedeck.search(music_dir)
    assert len(search) == 3
