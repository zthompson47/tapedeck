"""Tests for the keyboard module."""
from contextlib import contextmanager
import logging
import os
import pty
import sys

from reel.keyboard import Keyboard

LOGGER = logging.getLogger(__name__)


@contextmanager
def pty_stdin():
    """Replace stdin with a pty in a context."""
    _stashed_stdin = sys.stdin
    master, slave = pty.openpty()
    sys.stdin = open(master, 'rb')
    yield slave
    sys.stdin = _stashed_stdin


def test_keyboard_context():
    """Open a keyboard and writes some characters to it."""
    with pty_stdin() as slave:
        with Keyboard() as keyboard:
            os.write(slave, b'a')
            assert keyboard.has_input()
            assert keyboard.get_char() == b'a'
            bytes_written = os.write(slave, b'b')
            assert bytes_written == 1
            assert keyboard.has_input()
            assert keyboard.get_char() == b'b'
            os.write(slave, b'c')
            assert keyboard.has_input()
            assert keyboard.get_char() == b'c'
