"""A keylogger context manager."""
from contextlib import contextmanager
import fcntl
import io
import logging
import os
import pty
from select import select
import sys
import termios
import time
import tty

LOG = logging.getLogger(__name__)

K_UP = -1
K_DOWN = -2
K_LEFT = -3
K_RIGHT = -4


class Keyboard:
    """A way to get keyboard input, Posix-style."""

    def __init__(self):
        """Store the term settings before going into cbreak mode."""
        self._buff = bytearray()
        self._stashed_term = None

    def __enter__(self):
        """Save the current term and create a new one with no echo."""
        self._stashed_term = termios.tcgetattr(sys.stdin)

        # Set stdin file descriptor to non-blocking mode.
        fileno = sys.stdin.fileno()
        flag = fcntl.fcntl(fileno, fcntl.F_GETFL)
        fcntl.fcntl(fileno, fcntl.F_SETFL, flag | os.O_NONBLOCK)

        # Disable terminal echo and let ctl-c through.
        tty.setcbreak(sys.stdin, termios.TCSANOW)

        # Buffer any existing data from this fd.
        self._buffer_input()

        return self

    def __exit__(self, *args):
        """Bring back the original term settings."""
        termios.tcsetattr(sys.stdin, termios.TCSANOW, self._stashed_term)

    def _buffer_input(self):
        """Read as much data as we can from stdin and store in a buffer."""
        while True:
            result = sys.stdin.read(1024)
            if not result:
                break
            self._buff.extend(result.encode('utf-8'))

    def has_input(self):  # pylint: disable=no-self-use
        """Check if there is data in the buffer or on the wire."""
        if self._buff:
            return True

        rlist, _wlist, _xlist = select([sys.stdin], [], [], 0)
        if rlist:
            return True

        return False

    def get_char(self):  # pylint: disable=no-self-use
        """Read a unicode character from stdin."""
        char = None
        self._buffer_input()
        if self._buff:
            char = bytes(chr(self._buff.pop(0)).encode('utf-8'))
        if ord(char) == 27:
            if len(self._buff) == 2:
                next_two = self._buff[0:2]
                self._buff = self._buff[2:]
                if next_two[0] == 91:
                    if next_two[1] == 68:
                        char = K_LEFT
                    elif next_two[1] == 67:
                        char = K_RIGHT
                    elif next_two[1] == 66:
                        char = K_DOWN
                    elif next_two[1] == 65:
                        char = K_UP
            return char
        return char.decode('utf-8')

    def drain(self):
        """Read all we can into the buffer and throw it away."""
        self._buffer_input()
        self._buff.clear()


@contextmanager
def pty_stdin(preload=None):
    """Replace stdin with a pty."""
    _stashed_stdin = sys.stdin
    master, slave = pty.openpty()
    sys.stdin = io.TextIOWrapper(open(slave, 'rb'))

    def stdin(text):
        """Write data to pty and return bytes written."""
        LOG.debug('writing %s', text)
        if isinstance(text, str):
            return os.write(master, str.encode(text))
        return os.write(master, text)
    if preload:
        bytes_written = stdin(preload)
        LOG.debug('bytes: %d', bytes_written)

    yield stdin

    # Put stdin back.
    sys.stdin = _stashed_stdin


def main():
    """Test the keyboard out in a polling loop."""
    with Keyboard() as keyboard:
        while True:
            time.sleep(0.01)
            if keyboard.has_input():
                char = keyboard.get_char()
                if char == 'q':
                    break
                # print(chr(ord(char) + 1), end='')
                print(char, end='')
                sys.stdout.flush()
    print('\nexiting in a few seconds...')
    for _ in range(0, 10):
        # should be out of cbreak mode now
        time.sleep(0.3)


if __name__ == '__main__':
    main()
