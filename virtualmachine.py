import logging
import os
from time import sleep

from util import to_bits

log = logging.getLogger()
log.setLevel(logging.DEBUG)

# ch = logging.StreamHandler(sys.stdout)
fh = logging.FileHandler('/dev/pts/1')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(message)s')
fh.setFormatter(formatter)
log.addHandler(fh)


class VirtualMachine(object):
    memory = None
    V = None
    I = None
    pc = None
    gfx_buffer = None
    needs_refresh = False

    delay_timer = None
    sound_timer = None
    stack = None

    # Memory before this address is reserved for other purposes
    PROGRAM_START = 0x200

    # Height and width of screen
    SCREEN_HEIGHT = 32
    SCREEN_WIDTH = 64

    # Mapping of opcodes to functions that handle them
    function_map = None

    def initialize(self, program_path=None, program_raw=None):
        if not program_path and not program_raw:
            raise Exception("Path or binary are required")

        # 4K memory
        # 0x000-0x1FF - Chip 8 interpreter (contains font set in emu)
        # 0x050-0x0A0 - Used for the built in 4x5 pixel font set (0-F)
        # 0x200-0xFFF - Program ROM and work RAM
        self.memory = 4096 * [0]

        if program_path:
            self._load_program(program_path)
        else:
            self._load(program_raw, raw=True)

        # Setup the opcode/function mapping
        self._init_func_map()

        # Program counter is initialized to offset of 512 bytes
        self.pc = self.PROGRAM_START

        # CHIP-8 has 16 8-bit data registers named from V0 to VF. The VF register doubles as a carry flag.
        self.V = 16 * [0]

        # Index into memory
        self.I = 0

        # Graphics buffer
        self.gfx_buffer = (64 * 32) * [0]

        # Counts down to zero
        self.delay_timer = 0

        # Buzzes when reaches zero
        self.sound_timer = 0

        # Stack for tracking jumps
        self.stack = list()

    def tick(self):
        opcode = self._fetch_next()
        self._decode_exec(opcode)

    def _fetch_next(self):
        # Chip8 opcodes are two bytes. Merge two bytes from pc to obtain the complete opcode
        opcode = self.memory[self.pc] << 8 | self.memory[self.pc + 1]
        # Increment the program counter
        self.pc += 2
        return opcode

    def _decode_exec(self, opcode):
        try:
            res = opcode & 0xF000
            # First 4 bits are off, could be cls or ret
            if res == 0x0000:
                func = self.function_map[opcode & 0x00FF]
            # The 8 space is shared, extract the first and last bits to determine what we have
            elif res == 0x8000:
                func = self.function_map[res & 0xF00F]
            # The E and F space is also shared. The second half of the first byte tells us what we have
            elif res == 0xE000:
                func = self.function_map[opcode & 0xF0FF]
            elif res == 0xF000:
                func = self.function_map[opcode & 0xF0FF]
            else:
                func = self.function_map[opcode & 0xF000]

            # Execute the function that is mapped to this opcode
            func(opcode)
        except KeyError, e:
            if opcode:
                log.error("Unknown opcode: %s - %s" % (hex(opcode), e.message))

    def _load_program(self, program_path):
        if not os.path.exists(program_path):
            raise Exception("No such path: %s" % program_path)
        elif not os.path.isfile(program_path):
            raise Exception("Not a valid file: %s" % program_path)
        with open(program_path, 'rb') as f:
            self._load(f.read())

    def _load(self, bytes, raw=False):
        """load program into memory at offset of 512 bytes"""
        for idx, byte in enumerate(bytes):
            if raw:
                self.memory[self.PROGRAM_START + idx] = byte
            else:
                self.memory[self.PROGRAM_START + idx] = ord(byte)

    def _init_func_map(self):
        self.function_map = {0xE0: self.cls,
                             0xEE: self.ret,
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

    def _get_x(self, opcode):
        return (opcode & 0x0F00) >> 8

    def _get_y(self, opcode):
        return (opcode & 0x00F0) >> 4

    def _get_kk(self, opcode):
        return opcode & 0x00FF

    def cls(self, opcode):
        """
        Clear the display.

        Opcode: 00E0
        """
        log.debug("%s - cls()" % hex(opcode))
        exit()

    def ret(self, opcode):
        """
        Return from a subroutine.

        The interpreter sets the program counter to the address at the top of the stack,
        then subtracts 1 from the stack pointer.

        Opcode: 00EE
        """
        log.debug("%s: ret()" % hex(opcode))
        self.pc = self.stack.pop()

    def jmp_nnn(self, opcode):
        """
        1nnn - JP addr
        Jump to location nnn.

        The interpreter sets the program counter to nnn.
        """
        jump_addr = opcode & 0x0FFF
        log.debug("%s: jmp_nnn %s -> %s" % (hex(opcode), self.pc - 2, jump_addr))
        self.pc = jump_addr

    def call_nnn(self, opcode):
        """
        2nnn - CALL addr
        Call subroutine at nnn.

        The interpreter increments the stack pointer, then puts the current PC
        on the top of the stack. The PC is then set to nnn.
        """
        log.debug("%s: call_nnn()" % hex(opcode))
        self.stack.append(self.pc)
        self.pc = opcode & 0x0FFF

    def se_vx_kk(self, opcode):
        """
        3xkk - SE Vx, byte
        Skip next instruction if Vx = kk.

        The interpreter compares register Vx to kk, and if they are equal, increments the program counter by 2.
        """
        x = self._get_x(opcode)
        kk = self._get_kk(opcode)
        Vx = self.V[x]
        if Vx == kk:
            self.pc += 2
        log.debug("%s: se_vx_kk(V[x]=%s, kk=%s)" % (hex(opcode), Vx, kk))

    def sne_vx_kk(self, opcode):
        """
        4xkk - SNE Vx, byte
        Skip next instruction if Vx != kk.

        The interpreter compares register Vx to kk, and if they are not equal, increments the program counter by 2.
        """
        log.debug("%s - sne_vx_kk()" % hex(opcode))
        exit()

    def se_vx_vy(self, opcode):
        """
        5xy0 - SE Vx, Vy
        Skip next instruction if Vx = Vy.

        The interpreter compares register Vx to register Vy, and if they are equal,
        increments the program counter by 2.
        """
        log.debug("%s - se_vx_vy()" % hex(opcode))
        exit()

    def put_vx_kk(self, opcode):
        """
        6xkk - LD Vx, byte
        Set Vx = kk.

        The interpreter puts the value kk into register Vx.
        """
        x = self._get_x(opcode)
        kk = self._get_kk(opcode)
        self.V[x] = kk
        log.debug("%s: put_vx_kk(x=%s, kk=%s)" % (hex(opcode), x, kk))

    def add_vx_kk(self, opcode):
        """
        7xkk - ADD Vx, byte
        Set Vx = Vx + kk.

        Adds the value kk to the value of register Vx, then stores the result in Vx.
        """
        x = self._get_x(opcode)
        kk = self._get_kk(opcode)
        self.V[x] += kk
        log.debug("%s: add_vx_kk(x=%s, kk=%s)" % (hex(opcode), x, kk))

    def load_vy_vx(self, opcode):
        """
        8xy0 - LD Vx, Vy
        Set Vx = Vy.

        Stores the value of register Vy in register Vx.
        """
        log.debug("%s - load_vy_vx()" % hex(opcode))
        exit()

    def or_vx_vy(self, opcode):
        """
        8xy1 - OR Vx, Vy
        Set Vx = Vx OR Vy.

        Performs a bitwise OR on the values of Vx and Vy, then stores the result in Vx.
        """
        log.debug("%s - or_vx_vy()" % hex(opcode))
        exit()

    def and_vx_vy(self, opcode):
        """
        8xy2 - AND Vx, Vy
        Set Vx = Vx AND Vy.

        Performs a bitwise AND on the values of Vx and Vy, then stores the result in Vx
        """
        log.debug("%s - and_vx_vy()" % hex(opcode))
        exit()

    def xor_vx_vy(self, opcode):
        """
        8xy3 - XOR Vx, Vy
        Set Vx = Vx XOR Vy.

        Performs a bitwise exclusive OR on the values of Vx and Vy, then stores the result in Vx.
        """
        log.debug("%s - xor_vx_vy()" % hex(opcode))
        exit()

    def add_vx_vy(self, opcode):
        """
        8xy4 - ADD Vx, Vy
        Set Vx = Vx + Vy, set VF = carry.

        The values of Vx and Vy are added together. If the result is greater than 8 bits (i.e., > 255,)
        VF is set to 1, otherwise 0. Only the lowest 8 bits of the result are kept, and stored in Vx.
        """
        log.debug("%s - add_vx_vy()" % hex(opcode))
        exit()

    def sub_vx_vy(self, opcode):
        """
        8xy5 - SUB Vx, Vy
        Set Vx = Vx - Vy, set VF = NOT borrow.

        If Vx > Vy, then VF is set to 1, otherwise 0. Then Vy is subtracted from Vx, and the results stored in Vx.
        """
        log.debug("%s - sub_vx_vy()" % hex(opcode))
        exit()

    def shr_vx_vy(self, opcode):
        """
        8xy6 - SHR Vx {, Vy}
        Set Vx = Vx SHR 1.

        If the least-significant bit of Vx is 1, then VF is set to 1, otherwise 0. Then Vx is divided by 2.
        """
        log.debug("%s - shr_vx_vy()" % hex(opcode))
        exit()

    def subn_vx_vy(self, opcode):
        """
        8xy7 - SUBN Vx, Vy
        Set Vx = Vy - Vx, set VF = NOT borrow.

        If Vy > Vx, then VF is set to 1, otherwise 0. Then Vx is subtracted from Vy, and the results stored in Vx.
        """
        log.debug("%s - subn_vx_vy()" % hex(opcode))
        exit()

    def shl_vx_vy(self, opcode):
        """
        8xyE - SHL Vx {, Vy}
        Set Vx = Vx SHL 1.

        If the most-significant bit of Vx is 1, then VF is set to 1, otherwise to 0. Then Vx is multiplied by 2.
        """
        log.debug("%s - shl_vx_vy()" % hex(opcode))
        exit()

    def sne_vx_vy(self, opcode):
        """
        9xy0 - SNE Vx, Vy
        Skip next instruction if Vx != Vy.

        The values of Vx and Vy are compared, and if they are not equal, the program counter is increased by 2.
        """
        log.debug("%s - sne_vx_vy()" % hex(opcode))
        exit()

    def load_i(self, opcode):
        """
        Annn - LD I, addr
        Set I = nnn.

        The value of register I is set to nnn.
        """
        nnn = opcode & 0x0FFF
        self.I = nnn
        log.debug("%s: load_i(nnn=%s)" % (hex(opcode), nnn))

    def jmp_v0_nnn(self, opcode):
        """
        Bnnn - JP V0, addr
        Jump to location nnn + V0.

        The program counter is set to nnn plus the value of V0.
        """
        log.debug("%s - jmp_v0_nnn()" % hex(opcode))
        exit()

    def rand_kk_vx(self, opcode):
        """
        Cxkk - RND Vx, byte
        Set Vx = random byte AND kk.

        The interpreter generates a random number from 0 to 255, which is then ANDed with the value kk.
        The results are stored in Vx.
        """
        log.debug("%s - rand_kk_vx()" % hex(opcode))
        exit()

    def draw_vx_vy(self, opcode):
        """
        Dxyn - DRW Vx, Vy, nibble
        Display n-byte sprite starting at memory location I at (Vx, Vy), set VF = collision.

        The interpreter reads n bytes from memory, starting at the address stored in I.
        These bytes are then displayed as sprites on screen at coordinates (Vx, Vy).
        Sprites are XORed onto the existing screen. If this causes any pixels to be erased,
        VF is set to 1, otherwise it is set to 0. If the sprite is positioned so part of it
        is outside the coordinates of the display, it wraps around to the opposite side of the screen.
        """
        x = self.V[self._get_x(opcode)]
        y = self.V[self._get_y(opcode)]
        height = opcode & 0x000F

        log.debug("%s: draw_vx_vy(x=%s, y=%s, height=%s)" % (hex(opcode), x, y, height))
        for row, byte in enumerate(self.memory[self.I: self.I + height]):
            for col, bit in enumerate(to_bits(byte)):
                if bit:
                    index = (y + row) * self.SCREEN_WIDTH + (x + col)
                    self.V[0xF] = 1 if self.gfx_buffer[index] == 1 else 0
                    self.gfx_buffer[index] ^= 1
        self.needs_refresh = True
        log.debug('\n')

    def skip_vx(self, opcode):
        """
        Ex9E - SKP Vx
        Skip next instruction if key with the value of Vx is pressed.

        Checks the keyboard, and if the key corresponding to the value of Vx is currently in the down position,
        PC is increased by 2.
        """
        log.debug("%s - skip_vx()" % hex(opcode))
        exit()

    def nskip_vx(self, opcode):
        """
        ExA1 - SKNP Vx
        Skip next instruction if key with the value of Vx is not pressed.

        Checks the keyboard, and if the key corresponding to the value of Vx is currently in the up position,
        PC is increased by 2.
        """
        log.debug("%s - nskip_vx()" % hex(opcode))
        exit()

    def load_vx_dt(self, opcode):
        """
        Fx07 - LD Vx, DT
        Set Vx = delay timer value.

        The value of DT is placed into Vx.
        """
        log.debug("%s - load_vx_dt()" % hex(opcode))
        exit()

    def load_vx_k(self, opcode):
        """
        Fx0A - LD Vx, K
        Wait for a key press, store the value of the key in Vx.

        All execution stops until a key is pressed, then the value of that key is stored in Vx.
        """
        log.debug("%s - load_vx_k()" % hex(opcode))
        exit()

    def load_dt_vx(self, opcode):
        """
        Fx15 - LD DT, Vx
        Set delay timer = Vx.

        DT is set equal to the value of Vx.
        """
        log.debug("%s - load_dt_vx()" % hex(opcode))
        exit()

    def load_st_vx(self, opcode):
        """
        Fx18 - LD ST, Vx
        Set sound timer = Vx.

        ST is set equal to the value of Vx.
        """
        log.debug("%s - load_st_vx()" % hex(opcode))
        exit()

    def add_i_vx(self, opcode):
        """
        Fx1E - ADD I, Vx
        Set I = I + Vx.

        The values of I and Vx are added, and the results are stored in I.
        """
        x = self._get_x(opcode)
        self.I += self.V[x]
        log.debug("%s: add_i_vx()" % hex(opcode))

    def load_f_vx(self, opcode):
        """
        Fx29 - LD F, Vx
        Set I = location of sprite for digit Vx.

        The value of I is set to the location for the hexadecimal sprite corresponding to the value of Vx. See section 2.4
        """
        log.debug("%s - load_f_vx()" % hex(opcode))
        exit()

    def load_b_vx(self, opcode):
        """
        Fx33 - LD B, Vx
        Store BCD representation of Vx in memory locations I, I+1, and I+2.

        The interpreter takes the decimal value of Vx, and places the hundreds digit in memory at location in I,
        the tens digit at location I+1, and the ones digit at location I+2.
        """
        log.debug("%s - load_b_vx()" % hex(opcode))
        exit()

    def load_i_vx(self, opcode):
        """
        Fx55 - LD [I], Vx
        Store registers V0 through Vx in memory starting at location I.

        The interpreter copies the values of registers V0 through Vx into memory, starting at the address in I.
        """
        log.debug("%s - load_i_vx()" % hex(opcode))
        exit()

    def load_vx_i(self, opcode):
        """
        Fx65 - LD Vx, [I]
        Read registers V0 through Vx from memory starting at location I.

        The interpreter reads values from memory starting at location I into registers V0 through Vx.
        """
        log.debug("%s - load_vx_i()" % hex(opcode))
        exit()

# code = [0xf21e, 0xf21e]
#
# i = VirtualMachine()
# # i.run(program_raw=code)
#
# i.initialize(program_path='/home/facetoe/Downloads/chio/INVADERS')
# for _ in range(50):
#     i.tick()
#     sleep(0.2)
