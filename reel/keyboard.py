"""A keylogger context manager."""
from contextlib import contextmanager
import fcntl
import io
import logging
import os
import pty
import sys
import termios
import time
import tty

import trio

LOG = logging.getLogger(__name__)

KEY_EOT = b'\x04'
KEY_ESC = b'\x1b'

KEY_UP = b'\x1b[A'
KEY_DOWN = b'\x1b[B'
KEY_RIGHT = b'\x1b[C'
KEY_LEFT = b'\x1b[D'


class Keyboard:
    """A way to get keyboard input on Posix systems."""

    def __init__(self):
        """Store the term settings before going into cbreak mode."""
        self._break_on_eot = None
        self._stashed_term = None

        # Set stdin file descriptor to non-blocking mode
        fileno = sys.stdin.fileno()
        flag = fcntl.fcntl(fileno, fcntl.F_GETFL)
        fcntl.fcntl(fileno, fcntl.F_SETFL, flag | os.O_NONBLOCK)

    async def __aenter__(self):
        """Alias the sync func."""
        return self.__enter__()

    def __enter__(self):
        """Save the current term and create a new one with no echo."""
        try:
            self._stashed_term = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin, termios.TCSANOW)
        except termios.error:
            LOG.debug('No termios', exc_info=True)
        return self

    async def __aexit__(self, *args):
        """Bring back the original term settings."""
        self.__exit__(args)

    def __exit__(self, *args):
        """Bring back the original term settings."""
        if self._stashed_term:
            termios.tcsetattr(
                sys.stdin,
                termios.TCSANOW,
                self._stashed_term
            )

    def __aiter__(self):
        """Return iterator object."""
        return self

    async def __anext__(self):
        """Iterate over the input streamReturn the next character."""
        with block_stdin(True):
            char = await trio.run_sync_in_worker_thread(
                self.read,
                cancellable=True
            )
        if char == self._break_on_eot:
            raise StopAsyncIteration
        return char

    def break_on_eot(self, character=KEY_EOT):
        """Set an eot character to break from an iterator."""
        self._break_on_eot = character

    def read(self):  # pylint: disable=no-self-use
        """Read a unicode character from stdin.

        https://en.wikipedia.org/wiki/ANSI_escape_code#Escape_sequences
        """
        char = sys.stdin.read(1)
        if char != '' and ord(char) == ord(KEY_ESC):

            with block_stdin(False):
                csi = sys.stdin.read(1)
                if csi == '[':
                    ctl = sys.stdin.read(1)
                    if ctl == 'A':
                        return KEY_UP
                    if ctl == 'B':
                        return KEY_DOWN
                    if ctl == 'C':
                        return KEY_RIGHT
                    if ctl == 'D':
                        return KEY_LEFT

            return KEY_ESC
        return char


@contextmanager
def block_stdin(block: bool) -> None:
    """Toggle stdin blocking mode."""
    fileno = sys.stdin.fileno()
    flag = fcntl.fcntl(fileno, fcntl.F_GETFL)

    if block:
        fcntl.fcntl(fileno, fcntl.F_SETFL, flag | ~os.O_NONBLOCK)
    else:
        fcntl.fcntl(fileno, fcntl.F_SETFL, flag | os.O_NONBLOCK)

    yield

    fcntl.fcntl(fileno, fcntl.F_SETFL, flag)


@contextmanager
def pty_stdin(preload=None):
    """Replace stdin with a pty.

    Returns:
        A function to write data into stdin.

    Examples:
        >>> with pty_stdin('ab') as stdin:
        ...     with Keyboard() as keyboard:
        ...         assert keyboard.read() == 'a'
        ...         assert keyboard.read() == 'b'
        ...         stdin('x')
        ...         assert keyboard.read() == 'x'

    """
    _stashed_stdin = sys.stdin
    master, slave = pty.openpty()
    sys.stdin = io.TextIOWrapper(open(slave, 'rb'))

    def stdin(text):
        """Write data to the master side of the pty.

        Returns:
            Number of bytes written.

        Examples:
            >>> with pty_stdin() as stdin:
            ...   assert(stdin('a') == 1)

        """
        if isinstance(text, str):
            return os.write(master, str.encode(text))
        return os.write(master, text)

    if preload:
        bytes_written = stdin(preload)
        LOG.debug('bytes: %d', bytes_written)

    yield stdin

    sys.stdin = _stashed_stdin


def main():
    """Test the keyboard with a polling loop."""
    with Keyboard() as keyboard:
        while True:
            time.sleep(0.01)
            char = keyboard.read()
            if char == 'q':
                break
            print(char, end='')
            sys.stdout.flush()

    print('\n')
    print('Exiting in a few seconds, term should be back to normal...')
    time.sleep(3)


async def amain():
    """Test the keyboard with a polling loop, async."""
    async with Keyboard() as keyboard:
        keyboard.break_on_eot('q')
        async for key in keyboard:
            print(key, end='')
            sys.stdout.flush()
        print('')

if __name__ == '__main__':
    # main()
    trio.run(amain)
