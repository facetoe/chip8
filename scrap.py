from util import to_bits

V = 16 * [0]
V[0] = 1
V[11] = 1

I = 0

memory = [0x3C, 0xC3, 0xFF]

graphics = (64 * 32) * [0]


def draw_vx_vy():
    """
    Dxyn - DRW Vx, Vy, nibble
    Display n-byte sprite starting at memory location I at (Vx, Vy), set VF = collision.

    The interpreter reads n bytes from memory, starting at the address stored in I.
    These bytes are then displayed as sprites on screen at coordinates (Vx, Vy).
    Sprites are XORed onto the existing screen. If this causes any pixels to be erased,
    VF is set to 1, otherwise it is set to 0. If the sprite is positioned so part of it
    is outside the coordinates of the display, it wraps around to the opposite side of the screen.
    """
    opcode = 0xD003

    x = V[(opcode & 0x0F00) >> 8]
    y = V[(opcode & 0x00F0) >> 4]
    height = opcode & 0x000F

    for row, byte in enumerate(memory[I:I + height]):
        for col, bit in enumerate(to_bits(byte)):
            if bit:
                index = (row + y) * 64 + (col + x)
                if graphics[index] == 1:
                    V[0xF] = 1

                graphics[index] ^= 1
        print
    print graphics


# bytes = [0x3C, 0xC3, 0xFF]
# print bytes
draw_vx_vy()
print V[0xF]
