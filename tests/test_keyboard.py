"""Tests for the keyboard module."""
import logging

from reel.keyboard import (
    Keyboard,
    KEY_LEFT, KEY_RIGHT, KEY_UP, KEY_DOWN, KEY_ESC,
    pty_stdin
)

logging.basicConfig(filename='/Users/zach/kb.log', level=logging.DEBUG)
LOG = logging.getLogger(__name__)


def test_keyboard_context():
    """Open a keyboard and write some characters to it."""
    with pty_stdin('abc' * 1024) as stdin:
        with Keyboard() as keyboard:
            assert keyboard.read() == 'a'
            assert keyboard.read() == 'b'
            assert keyboard.read() == 'c'

            stdin('x')  # Goes to end of buffer

            # Drain buffer
            assert keyboard.read() == 'a'
            assert keyboard.read() == 'b'
            assert keyboard.read() == 'c'
            for _ in range(1018):
                assert keyboard.read()

            assert keyboard.read() == 'x'

            stdin('de')
            assert keyboard.read() == 'd'
            assert keyboard.read() == 'e'

            assert keyboard.read() == ''


def test_arrows():
    """Test the arrow keys."""
    k_left = bytearray([27, 91, 68])
    k_right = bytearray([27, 91, 67])
    k_down = bytearray([27, 91, 66])
    k_up = bytearray([27, 91, 65])
    k_esc = bytearray([27])
    with pty_stdin(k_left) as stdin:
        with Keyboard() as keyboard:
            assert keyboard.read() == KEY_LEFT
            stdin(k_right)
            assert keyboard.read() == KEY_RIGHT
            stdin(k_down)
            assert keyboard.read() == KEY_DOWN
            stdin(k_up)
            assert keyboard.read() == KEY_UP
            stdin(k_esc)
            assert keyboard.read() == KEY_ESC


async def test_keyboard_context_async():
    """The keyboard can be opened as a channel."""
    message = ['O', 'n', 'c', 'e', ' ', 'u', 'p', 'o']
    LOG.debug(message)
    with pty_stdin(''.join(message)) as stdin:
        async with Keyboard() as keyboard:
            keyboard.break_on_eot('o')
            async for key in keyboard:
                assert key == message.pop(0)
            stdin('a')
            assert keyboard.read() == 'a'
