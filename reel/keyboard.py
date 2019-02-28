"""A keylogger context manager."""
import logging
from select import select
import sys
import termios
import time
import tty

LOG = logging.getLogger(__name__)


class Keyboard:
    """A way to get keyboard input with non-blocking polling."""

    def __init__(self):
        """Store the term settings before going into cbreak mode."""
        self._stashed_term = None

    def __enter__(self):
        """Save the current term and create a new one with no echo."""
        self._stashed_term = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin)
        return self

    def __exit__(self, *args):
        """Bring back the original term settings."""
        termios.tcsetattr(sys.stdin, termios.TCSAFLUSH, self._stashed_term)

    def has_input(self):  # pylint: disable=no-self-use
        """Poll the keyboard for input."""
        rlist, _wlist, _xlist = select([sys.stdin], [], [], 0)
        if rlist:
            return True
        return False

    def get_char(self):  # pylint: disable=no-self-use
        """Read a character from stdin."""
        char = sys.stdin.read(1)
        # LOG.debug('char: %d', ord(char))
        # if ord(char) == 27:
        #     # might be an arrow key
        #     if self.has_input():
        #         char2 = sys.stdin.read(1)
        #         LOG.debug('char2: %d', ord(char2))
        #         if ord(char2) == 91:
        #             if self.has_input():
        #                 char3 = sys.stdin.read(1)
        #                 LOG.debug('char3: %d', ord(char3))
        #                 if ord(char3) == 68:
        #                     char = Keyboard.LEFT
        #                 elif ord(char3) == 67:
        #                     char = Keyboard.RIGHT
        #                 elif ord(char3) == 66:
        #                     char = Keyboard.DOWN
        #                 elif ord(char3) == 65:
        #                     char = Keyboard.UP
        return char


def main():
    """Test the keyboard out."""
    with Keyboard() as keyboard:
        while True:
            if keyboard.has_input():
                char = keyboard.get_char()
                if char == 'q':
                    print('Exiting...')
                    break
                print(char, end='')
                sys.stdout.flush()
    for _ in range(0, 10):
        time.sleep(0.3)


if __name__ == '__main__':
    main()
