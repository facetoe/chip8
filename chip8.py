import logging
import os
import sys
from time import sleep

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
                res = self.opcode & 0xF000
                # First 4 bits are off, could be cls or ret
                if res == 0x0000:
                    self.function_map[self.opcode]()
                # The 8 space is shared, extract the first and last bits to determine what we have
                elif res == 0x8000:
                    self.function_map[res & 0xF00F]()
                # The E and F space is also shared. The second half of the first byte tells us what we have
                elif res == 0xe000 or res == 0xf000:
                    self.function_map[res & 0xF0FF]()
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
                             0x1000: self.jmp_nnn,
                             0x2000: self.call_nnn,
                             0x3000: self.se_vx_kk,
                             0x4000: self.sne_vx_kk,
                             0x5000: self.se_vx_vy,
                             0x6000: self.put_vx_kk,
                             0x7000: self.add_vx_kk,
                             0x8000: self.load_vy_vx,
                             0x8001: self.or_vx_vy,
                             0x8002: self.and_vx_vy,
                             0x8003: self.xor_vx_vy,
                             0x8004: self.add_vx_vy,
                             0x8005: self.sub_vx_vy,
                             0x8006: self.shr_vx_vy,
                             0x8007: self.subn_vx_vy,
                             0x800E: self.shl_vx_vy,
                             0x9000: self.sne_vx_vy,
                             0xA000: self.load_i,
                             0xB000: self.jmp_v0_nnn,
                             0xC000: self.rand_kk_vx,
                             0xD000: self.draw_vx_vy,
                             0xE09E: self.skip_vx,
                             0xE0A1: self.nskip_vx,
                             0xF007: self.load_dt_vx,
                             0xF00A: self.load_vx_k,
                             0xF015: self.load_dt_vx,
                             0xF018: self.load_st_vx,
                             0xF01E: self.add_i_vx,
                             0xF029: self.load_f_vx,
                             0xF033: self.load_b_vx,
                             0xF055: self.load_i_vx,
                             0xF065: self.load_vx_i
                             }

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

    def jmp_nnn(self):
        """
        1nnn - JP addr
        Jump to location nnn.

        The interpreter sets the program counter to nnn.
        """
        log.debug("%s - jmp()" % hex(self.opcode))
        self.pc = self.opcode & 0x0FFF

    def call_nnn(self):
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

    def or_vx_vy(self):
        """
        8xy1 - OR Vx, Vy
        Set Vx = Vx OR Vy.

        Performs a bitwise OR on the values of Vx and Vy, then stores the result in Vx.
        """
        log.debug("%s - or_vx_vy()" % hex(self.opcode))

    def and_vx_vy(self):
        """
        8xy2 - AND Vx, Vy
        Set Vx = Vx AND Vy.

        Performs a bitwise AND on the values of Vx and Vy, then stores the result in Vx
        """
        log.debug("%s - and_vx_vy()" % hex(self.opcode))

    def xor_vx_vy(self):
        """
        8xy3 - XOR Vx, Vy
        Set Vx = Vx XOR Vy.

        Performs a bitwise exclusive OR on the values of Vx and Vy, then stores the result in Vx.
        """
        log.debug("%s - xor_vx_vy()" % hex(self.opcode))

    def add_vx_vy(self):
        """
        8xy4 - ADD Vx, Vy
        Set Vx = Vx + Vy, set VF = carry.

        The values of Vx and Vy are added together. If the result is greater than 8 bits (i.e., > 255,)
        VF is set to 1, otherwise 0. Only the lowest 8 bits of the result are kept, and stored in Vx.
        """
        log.debug("%s - add_vx_vy()" % hex(self.opcode))

    def sub_vx_vy(self):
        """
        8xy5 - SUB Vx, Vy
        Set Vx = Vx - Vy, set VF = NOT borrow.

        If Vx > Vy, then VF is set to 1, otherwise 0. Then Vy is subtracted from Vx, and the results stored in Vx.
        """
        log.debug("%s - sub_vx_vy()" % hex(self.opcode))

    def shr_vx_vy(self):
        """
        8xy6 - SHR Vx {, Vy}
        Set Vx = Vx SHR 1.

        If the least-significant bit of Vx is 1, then VF is set to 1, otherwise 0. Then Vx is divided by 2.
        """
        log.debug("%s - shr_vx_vy()" % hex(self.opcode))

    def subn_vx_vy(self):
        """
        8xy7 - SUBN Vx, Vy
        Set Vx = Vy - Vx, set VF = NOT borrow.

        If Vy > Vx, then VF is set to 1, otherwise 0. Then Vx is subtracted from Vy, and the results stored in Vx.
        """
        log.debug("%s - subn_vx_vy()" % hex(self.opcode))

    def shl_vx_vy(self):
        """
        8xyE - SHL Vx {, Vy}
        Set Vx = Vx SHL 1.

        If the most-significant bit of Vx is 1, then VF is set to 1, otherwise to 0. Then Vx is multiplied by 2.
        """
        log.debug("%s - shl_vx_vy()" % hex(self.opcode))

    def sne_vx_vy(self):
        """
        9xy0 - SNE Vx, Vy
        Skip next instruction if Vx != Vy.

        The values of Vx and Vy are compared, and if they are not equal, the program counter is increased by 2.
        """
        log.debug("%s - sne_vx_vy()" % hex(self.opcode))

    def load_i(self):
        """
        Annn - LD I, addr
        Set I = nnn.

        The value of register I is set to nnn.
        """
        log.debug("%s - load_i()" % hex(self.opcode))

    def jmp_v0_nnn(self):
        """
        Bnnn - JP V0, addr
        Jump to location nnn + V0.

        The program counter is set to nnn plus the value of V0.
        """
        log.debug("%s - jmp_v0_nnn()" % hex(self.opcode))

    def rand_kk_vx(self):
        """
        Cxkk - RND Vx, byte
        Set Vx = random byte AND kk.

        The interpreter generates a random number from 0 to 255, which is then ANDed with the value kk.
        The results are stored in Vx.
        """
        log.debug("%s - rand_kk_vx()" % hex(self.opcode))

    def draw_vx_vy(self):
        """
        Dxyn - DRW Vx, Vy, nibble
        Display n-byte sprite starting at memory location I at (Vx, Vy), set VF = collision.

        The interpreter reads n bytes from memory, starting at the address stored in I.
        These bytes are then displayed as sprites on screen at coordinates (Vx, Vy).
        Sprites are XORed onto the existing screen. If this causes any pixels to be erased,
        VF is set to 1, otherwise it is set to 0. If the sprite is positioned so part of it
        is outside the coordinates of the display, it wraps around to the opposite side of the screen.
        """
        log.debug("%s - draw_vx_vy()" % hex(self.opcode))

    def skip_vx(self):
        """
        Ex9E - SKP Vx
        Skip next instruction if key with the value of Vx is pressed.

        Checks the keyboard, and if the key corresponding to the value of Vx is currently in the down position,
        PC is increased by 2.
        """
        log.debug("%s - skip_vx()" % hex(self.opcode))

    def nskip_vx(self):
        """
        ExA1 - SKNP Vx
        Skip next instruction if key with the value of Vx is not pressed.

        Checks the keyboard, and if the key corresponding to the value of Vx is currently in the up position,
        PC is increased by 2.
        """
        log.debug("%s - nskip_vx()" % hex(self.opcode))

    def load_vx_dt(self):
        """
        Fx07 - LD Vx, DT
        Set Vx = delay timer value.

        The value of DT is placed into Vx.
        """
        log.debug("%s - load_vx_dt()" % hex(self.opcode))

    def load_vx_k(self):
        """
        Fx0A - LD Vx, K
        Wait for a key press, store the value of the key in Vx.

        All execution stops until a key is pressed, then the value of that key is stored in Vx.
        """
        log.debug("%s - load_vx_k()" % hex(self.opcode))

    def load_dt_vx(self):
        """
        Fx15 - LD DT, Vx
        Set delay timer = Vx.

        DT is set equal to the value of Vx.
        """
        log.debug("%s - load_dt_vx()" % hex(self.opcode))

    def load_st_vx(self):
        """
        Fx18 - LD ST, Vx
        Set sound timer = Vx.

        ST is set equal to the value of Vx.
        """
        log.debug("%s - load_st_vx()" % hex(self.opcode))

    def add_i_vx(self):
        """
        Fx1E - ADD I, Vx
        Set I = I + Vx.

        The values of I and Vx are added, and the results are stored in I.
        """
        log.debug("%s - add_i_vx()" % hex(self.opcode))

    def load_f_vx(self):
        """
        Fx29 - LD F, Vx
        Set I = location of sprite for digit Vx.

        The value of I is set to the location for the hexadecimal sprite corresponding to the value of Vx. See section 2.4
        """
        log.debug("%s - load_f_vx()" % hex(self.opcode))

    def load_b_vx(self):
        """
        Fx33 - LD B, Vx
        Store BCD representation of Vx in memory locations I, I+1, and I+2.

        The interpreter takes the decimal value of Vx, and places the hundreds digit in memory at location in I,
        the tens digit at location I+1, and the ones digit at location I+2.
        """
        log.debug("%s - load_b_vx()" % hex(self.opcode))

    def load_i_vx(self):
        """
        Fx55 - LD [I], Vx
        Store registers V0 through Vx in memory starting at location I.

        The interpreter copies the values of registers V0 through Vx into memory, starting at the address in I.
        """
        log.debug("%s - load_i_vx()" % hex(self.opcode))

    def load_vx_i(self):
        """
        Fx65 - LD Vx, [I]
        Read registers V0 through Vx from memory starting at location I.

        The interpreter reads values from memory starting at location I into registers V0 through Vx.
        """
        log.debug("%s - load_vx_i()" % hex(self.opcode))

    def _fetch(self):
        # chip8 opcodes are two bytes. Merge two bytes from pc to obtain the complete opcode
        return self.memory[self.pc] << 8 | self.memory[self.pc + 1]


i = Interpreter()

i.run('/home/facetoe/Downloads/chio/INVADERS')
