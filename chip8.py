import curses
from time import sleep

from lib.vm import VirtualMachine

from lib.io import IO


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
