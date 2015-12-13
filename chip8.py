import logging
import os
import sys

log = logging.getLogger()
log.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(message)s')
ch.setFormatter(formatter)
log.addHandler(ch)


class Interpreter(object):
    memory = None
    V = None
    I = None
    pc = None
    gfx = None

    delay_timer = None
    sound_timer = None
    stack = None
    opcode = None

    # Memory before this address is reserved for other purposes
    PROGRAM_START = 0x200

    # Mapping of opcodes to functions that handle them
    function_map = None

    def initialize(self, program_path):
        # 4K memory
        # 0x000-0x1FF - Chip 8 interpreter (contains font set in emu)
        # 0x050-0x0A0 - Used for the built in 4x5 pixel font set (0-F)
        # 0x200-0xFFF - Program ROM and work RAM
        self.memory = 4096 * [0]

        # Program counter is initialized to offset of 512 bytes
        self.pc = self.PROGRAM_START

        # CHIP-8 has 16 8-bit data registers named from V0 to VF. The VF register doubles as a carry flag.
        self.V = 16 * [0]

        # Memory index
        self.I = 0

        # Graphics
        self.gfx = (64 * 32) * [0]

        # Counts down to zero
        self.delay_timer = 0

        # Buzzes when reaches zero
        self.sound_timer = 0

        # Stack
        self.stack = list()

        self._load_program(program_path)
        self._init_func_map()

    def run(self, program_path):
        self.initialize(program_path)
        while self.pc < len(self.memory):
            self.opcode = self._fetch()
            self.pc += 2

            try:
                # First 4 bits are off, could be cls or ret
                if self.opcode & 0xF000 == 0x0000:
                    self.function_map[self.opcode]()
                else:
                    self.function_map[self.opcode & 0xF000]()
            except Exception:
                if self.opcode:
                    pass
                    log.error("Unknown opcode: %s" % hex(self.opcode))

    def _load_program(self, program_path):
        if not os.path.exists(program_path):
            raise Exception("No such path: %s" % program_path)
        elif not os.path.isfile(program_path):
            raise Exception("Not a valid file: %s" % program_path)

        with open(program_path, 'rb') as f:
            for idx, byte in enumerate(f.read()):
                # load program into memory at offset of 512 bytes
                self.memory[self.PROGRAM_START + idx] = ord(byte)

    def _init_func_map(self):
        self.function_map = {0x00E0: self.cls,
                             0x00EE: self.ret,
                             0x1000: self.jmp,
                             0x20000: self.call,
                             0x30000: self.se_vx_kk,
                             0x40000: self.sne_vx_kk,
                             0x50000: self.se_vx_vy,
                             0x06000: self.put_vx_kk}

    def cls(self):
        """
        Clear the display.

        Opcode: 00E0
        """
        log.debug("%s - cls()" % hex(self.opcode))

    def ret(self):
        """
        Return from a subroutine.

        The interpreter sets the program counter to the address at the top of the stack,
        then subtracts 1 from the stack pointer.

        Opcode: 00EE
        """
        log.debug("%s - ret()" % hex(self.opcode))
        self.pc = self.stack.pop()

    def jmp(self):
        """
        1nnn - JP addr
        Jump to location nnn.

        The interpreter sets the program counter to nnn.
        """
        log.debug("%s - jmp()" % hex(self.opcode))
        self.pc = self.opcode & 0x0FFF

    def call(self):
        """
        2nnn - CALL addr
        Call subroutine at nnn.

        The interpreter increments the stack pointer, then puts the current PC
        on the top of the stack. The PC is then set to nnn.
        """
        log.debug("%s - call()" % hex(self.opcode))
        self.stack.append(self.pc)
        self.pc = self.opcode & 0x0FFF

    def se_vx_kk(self):
        """
        3xkk - SE Vx, byte
        Skip next instruction if Vx = kk.

        The interpreter compares register Vx to kk, and if they are equal, increments the program counter by 2.
        """
        log.debug("%s - se_vx_kk()" % hex(self.opcode))

    def sne_vx_kk(self):
        """
        4xkk - SNE Vx, byte
        Skip next instruction if Vx != kk.

        The interpreter compares register Vx to kk, and if they are not equal, increments the program counter by 2.
        """
        log.debug("%s - sne_vx_kk()" % hex(self.opcode))

    def se_vx_vy(self):
        """
        5xy0 - SE Vx, Vy
        Skip next instruction if Vx = Vy.

        The interpreter compares register Vx to register Vy, and if they are equal,
        increments the program counter by 2.
        """
        log.debug("%s - se_vx_vy()" % hex(self.opcode))

    def put_vx_kk(self):
        """
        6xkk - LD Vx, byte
        Set Vx = kk.

        The interpreter puts the value kk into register Vx.
        """
        log.debug("%s - put_vx_kk()" % hex(self.opcode))

    def add_vx_kk(self):
        """
        7xkk - ADD Vx, byte
        Set Vx = Vx + kk.

        Adds the value kk to the value of register Vx, then stores the result in Vx.
        """
        log.debug("%s - add_vx_kk()" % hex(self.opcode))

    def load_vy_vx(self):
        """
        8xy0 - LD Vx, Vy
        Set Vx = Vy.

        Stores the value of register Vy in register Vx.
        """
        log.debug("%s - load_vy_vx()" % hex(self.opcode))

    def _fetch(self):
        # chip8 opcodes are two bytes. Merge two bytes from pc to obtain the complete opcode
        return self.memory[self.pc] << 8 | self.memory[self.pc + 1]


i = Interpreter()

i.run('/home/facetoe/Downloads/chio/INVADERS')
