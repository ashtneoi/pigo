import logging
import time

import pigo


MCLR_N = 79
ICSPDAT = 84
ICSPCLK = 86


logger = logging.getLogger(__name__)


def sleep(n):
    logger.debug("-")
    time.sleep(n)


def reverse_bits(data, length):
    data2 = 0
    for _ in range(length):
        data2 <<= 1
        data2 |= data & 1
        data >>= 1
    return data2


def send(g, data, length):
    """Send `length` bits of `data` LSb first

    ICSPCLK must be low when this function is called.
    """

    for _ in range(length):
        bit = data & 1
        g.set_value(ICSPDAT, bit)
        g.set_value(ICSPCLK, 1)
        sleep(.005)
        g.set_value(ICSPCLK, 0)
        sleep(.005)

        data >>= 1


def recv(g, length):
    """Receive `length` bits LSb first

    ICSPCLK must be low and ICSPDAT must be configured as an input when this
    function is called.
    """

    data = 0

    for _ in range(length):
        data >>= 1

        g.set_value(ICSPCLK, 1)
        sleep(.005)

        bit = g.get_value(ICSPDAT)
        data |= bit << (length - 1)
        g.set_value(ICSPCLK, 0)
        sleep(.005)

    return data


def enter_lvp_mode(g):
    # Hold in reset.

    g.set_value(MCLR_N, 0)
    sleep(.05)

    # Send LVP key sequence.

    g.set_value(ICSPCLK, 0)
    g.set_direction(ICSPDAT, "out")
    sleep(.05)

    key_sequence = 0x4D434850  # "MCHP"
    send(g, key_sequence, 32)
    send(g, 0, 1)
    sleep(.05)


def load_configuration(g, data):
    send(g, 0x00, 6)
    sleep(.05)
    send(g, data << 1, 16)
    sleep(.05)


def read_data_from_program_memory(g):
    send(g, 0x04, 6)
    g.set_direction(ICSPDAT, "in")
    sleep(.05)
    data = recv(g, 16)
    g.set_direction(ICSPDAT, "out")
    sleep(.05)

    return (data >> 1) & 0x3FFF


def increment_address(g):
    send(g, 0x06, 6)
    sleep(.05)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    g = pigo.GpioManager()
    with g:
        # Exit programming mode, if active.
        g.set_value(MCLR_N, 1)
        sleep(.5)

        enter_lvp_mode(g)

        load_configuration(g, 0x00)

        for _ in range(12):
            data = read_data_from_program_memory(g)
            print(f"0x{data:X}")

            increment_address(g)

        g.set_direction(ICSPDAT, "in")
        g.set_direction(ICSPCLK, "in")
        g.set_direction(MCLR_N, "in")
