import curses
stdscr = curses.initscr()
curses.noecho()
curses.cbreak()
stdscr.keypad(True)
curses.nocbreak()
stdscr.keypad(False)
curses.echo()
curses.endwin()
