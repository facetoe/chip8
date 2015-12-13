import curses


class IO(object):
    win = None

    def initialize(self, screen):
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)

        screen.bkgd(curses.color_pair(1))
        screen.refresh()

        self.win = curses.newwin(32, 64, 5, 5)
        self.win.bkgd(curses.color_pair(2))

    def draw(self, startx, starty, graphics):
        for i, bit in enumerate(graphics):
            x, y = startx + (i % 32), starty + (i / 32)
            char = '*' if bit else " "
            if x < 61 and y < 31:
                self.win.addstr(y, x, char)
        self.win.box()
        self.win.refresh()
        self.win.getch()

# try:
#     curses.wrapper(main)
# except KeyboardInterrupt:
#     print("Got KeyboardInterrupt exception. Exiting...")
#     exit()
