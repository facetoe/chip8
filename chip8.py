import curses
from time import sleep

import logging

from io import IO
from virtualmachine import VirtualMachine


def main(screen):
    vm = VirtualMachine()
    vm.initialize(program_path='/home/facetoe/Downloads/chio/INVADERS')
    io = IO(screen)
    io.initialize(screen)

    while True:
        vm.tick()
        if vm.needs_refresh:
            io.draw(vm.gfx_buffer)
            vm.needs_refresh = False
        sleep(0.01)

try:
    curses.wrapper(main)
except KeyboardInterrupt:
    print("Got KeyboardInterrupt exception. Exiting...")
    exit()
