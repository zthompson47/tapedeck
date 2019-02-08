"""Test the pre-configured commands."""
# pylint: disable=W0611, W0621
import logging
import os

from trio import Path

from reel import cmd
from reel.cmd import ffmpeg, sox

BYTE_LIMIT = 1000000


async def test_audio_dir(audio_dir):
    """Get test audio files."""
    assert audio_dir.exists()


async def test_import():
    """Make sure the module is imported."""
    assert cmd
    assert cmd.SRC_SILENCE
