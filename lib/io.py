# coding: utf-8

import curses

import logging

log = logging.getLogger()
log.setLevel(logging.DEBUG)

# ch = logging.StreamHandler(sys.stdout)
fh = logging.FileHandler('/dev/pts/1')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(message)s')
fh.setFormatter(formatter)
log.addHandler(fh)

class IO(object):
    win = None

    SCREEN_HEIGHT = 32
    SCREEN_WIDTH = 64

    def __init__(self, screen):
        self.initialize(screen)

    def initialize(self, screen):
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_GREEN)

        screen.bkgd(curses.color_pair(1))
        screen.refresh()

        self.win = curses.newwin(self.SCREEN_HEIGHT, self.SCREEN_WIDTH, 0, 0)
        self.win.bkgd(curses.color_pair(2))

    def draw(self, graphics):
        self.win.clear()
        for i, bit in enumerate(graphics):
            width, height = (i % self.SCREEN_WIDTH), (i / self.SCREEN_WIDTH)
            char = '*' if bit else ""
            if height < self.SCREEN_HEIGHT-1 and width < self.SCREEN_WIDTH-1:
                self.win.addstr(height, width, char, curses.color_pair(3))

        self.win.box()
        self.win.refresh()
