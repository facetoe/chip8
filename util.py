def to_bits(byte_):
    """
    Yield each bit in byte_
    """
    for i in xrange(8):
        yield (byte_ >> i) & 1
