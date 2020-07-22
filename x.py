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
        sleep(.001)
        g.set_value(ICSPCLK, 0)
        sleep(.001)

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
        sleep(.001)

        bit = g.get_value(ICSPDAT)
        data |= bit << (length - 1)
        g.set_value(ICSPCLK, 0)
        sleep(.001)

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
    sleep(.001)
    send(g, data << 1, 16)
    sleep(.001)


def read_data_from_program_memory(g):
    send(g, 0x04, 6)
    g.set_direction(ICSPDAT, "in")
    sleep(.001)
    data = recv(g, 16)
    g.set_direction(ICSPDAT, "out")
    sleep(.001)

    return (data >> 1) & 0x3FFF


def increment_address(g):
    send(g, 0x06, 6)
    sleep(.001)


def reset_address(g):
    send(g, 0x16, 6)
    sleep(.001)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    g = pigo.GpioManager()
    with g:
        # Exit programming mode, if active.
        g.set_value(MCLR_N, 1)
        sleep(.5)

        enter_lvp_mode(g)

        config = {}
        for i in range(1000):
            print(f"=== Iteration {i} ===")

            load_configuration(g, 0x00)

            for addr in range(0x8000, 0x8018):
                data = read_data_from_program_memory(g)

                if i == 0:
                    print(f"[0x{addr:04X}]: 0x{data:04X}")
                    config[addr] = data
                elif config[addr] != data:
                    logger.error(
                        f"[0x{addr:04X}]: expected 0x{config[addr]:04X}, "
                        f"got 0x{data:04X}"
                    )

                increment_address(g)

            reset_address(g)

        g.set_direction(ICSPDAT, "in")
        g.set_direction(ICSPCLK, "in")
        g.set_direction(MCLR_N, "in")
