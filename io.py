import curses


class IO(object):
    win = None

    def __init__(self, screen):
        self.initialize(screen)

    def initialize(self, screen):
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)

        screen.bkgd(curses.color_pair(1))
        screen.refresh()

        self.win = curses.newwin(32, 64, 5, 5)
        self.win.bkgd(curses.color_pair(2))

    def draw(self, graphics):
        self.win.clear()
        for i, bit in enumerate(graphics):
            x, y = (i % 32), (i / 32)
            char = '*' if bit else ""
            if x < 61 and y < 31:
                self.win.addstr(y, x, char)
        self.win.box()
        self.win.refresh()
