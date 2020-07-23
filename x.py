import logging
import time

import pigo


MCLR_N = 79
ICSPDAT = 84
ICSPCLK = 86

T_CLK_HALF = 1e-6
T_DLY = 10e-6
T_PINT = 10e-3
T_ERAB = 10e-3
T_ERAR = 10e-3

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
        sleep(T_CLK_HALF)

        g.set_value(ICSPCLK, 0)
        sleep(T_CLK_HALF)

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
        sleep(T_CLK_HALF)

        bit = g.get_value(ICSPDAT)
        data |= bit << (length - 1)
        g.set_value(ICSPCLK, 0)
        sleep(T_CLK_HALF)

    return data


def enter_lvp_mode(g):
    # Hold in reset.

    g.set_value(MCLR_N, 0)
    sleep(.05)

    # Send LVP key sequence.

    key_sequence = 0x4D434850  # "MCHP"
    g.set_value(ICSPCLK, 0)
    g.set_direction(ICSPDAT, "out")
    send(g, key_sequence, 32)
    send(g, 0, 1)
    sleep(T_DLY)


def load_configuration(g, data):
    send(g, 0x00, 6)
    sleep(T_DLY)
    send(g, data << 1, 16)
    sleep(T_DLY)


def load_data_for_program_memory(g, data):
    send(g, 0x02, 6)
    sleep(T_DLY)
    send(g, data << 1, 16)
    sleep(T_DLY)


def read_data_from_program_memory(g):
    send(g, 0x04, 6)
    g.set_direction(ICSPDAT, "in")
    sleep(T_DLY)
    data = recv(g, 16)
    g.set_direction(ICSPDAT, "out")
    sleep(T_DLY)

    return (data >> 1) & 0x3FFF


def increment_address(g):
    send(g, 0x06, 6)
    sleep(T_DLY)


def reset_address(g):
    send(g, 0x16, 6)
    sleep(T_DLY)


def begin_internally_timed_programming(g):
    send(g, 0x08, 6)
    sleep(T_PINT)


def bulk_erase_program_memory(g):
    send(g, 0x09, 6)
    sleep(T_ERAB)


def row_erase_program_memory(g):
    send(g, 0x11, 6)
    sleep(T_ERAR)


def test_config_read_repeatability():
    g = pigo.GpioManager()
    with g:
        # Exit programming mode, if active.
        g.set_value(MCLR_N, 1)
        sleep(.05)

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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    test_config_read_repeatability()
