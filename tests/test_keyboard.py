"""Tests for the keyboard module."""
import logging

from reel.keyboard import (
    Keyboard,
    K_LEFT, K_RIGHT, K_UP, K_DOWN,
    pty_stdin
)

LOG = logging.getLogger(__name__)


def test_keyboard_context():
    """Open a keyboard and write some characters to it."""
    with pty_stdin('abc' * 1024) as stdin:
        with Keyboard() as keyboard:
            assert keyboard.has_input()
            assert keyboard.get_char() == 'a'
            assert keyboard.has_input()
            assert keyboard.get_char() == 'b'
            assert keyboard.has_input()
            assert keyboard.get_char() == 'c'

            stdin('x')  # goes to end of buffer

            assert keyboard.has_input()
            assert keyboard.get_char() == 'a'
            assert keyboard.has_input()
            assert keyboard.get_char() == 'b'
            assert keyboard.has_input()
            assert keyboard.get_char() == 'c'

            for _ in range(1018):
                assert keyboard.has_input()
                assert keyboard.get_char()
            assert keyboard.get_char() == 'x'

            keyboard.drain()

            stdin('de')
            assert keyboard.has_input()
            assert keyboard.get_char() == 'd'
            assert keyboard.has_input()
            assert keyboard.get_char() == 'e'

            assert not keyboard.has_input()


def test_arrows():
    """Test the arrow keys."""
    k_left = bytearray([27, 91, 68])
    k_right = bytearray([27, 91, 67])
    k_down = bytearray([27, 91, 66])
    k_up = bytearray([27, 91, 65])
    with pty_stdin(k_left) as stdin:
        with Keyboard() as keyboard:
            assert keyboard.has_input()
            assert keyboard.get_char() == K_LEFT

            stdin(k_right)
            assert keyboard.has_input()
            assert keyboard.get_char() == K_RIGHT

            stdin(k_down)
            assert keyboard.has_input()
            assert keyboard.get_char() == K_DOWN

            stdin(k_up)
            assert keyboard.has_input()
            assert keyboard.get_char() == K_UP
