import curses
import sys

import trio


async def main(stdscr):
    # stdscr.clear()
    stdscr.nodelay(True)
    msg = 'asdf'
    while True:
        print(msg)
        ch = stdscr.getch()
        if ch == curses.ERR:
            await trio.sleep(0.25)
        if ch == ord('q'):
            break
        if ch == ord('u'):
            msg = 'qwer'
        if ch == ord('i'):
            msg = 'zxcv'


returncode = 13
try:
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)

    returncode = trio.run(main, stdscr)

finally:
    curses.nocbreak()
    stdscr.keypad(False)
    curses.echo()
    curses.endwin()
    sys.exit(returncode)
