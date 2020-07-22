import logging


logger = logging.getLogger(__name__)


class GpioManager:
    def __enter__(self):
        self.pins = {}

    def _export(self, pin):
        with open(f"/sys/class/gpio/export", "w") as f:
            f.write(f"{pin}")
        self.pins[pin] = "in"

    def _unexport(self, pin):
        with open(f"/sys/class/gpio/unexport", "w") as f:
            f.write(f"{pin}")
        del self.pins[pin]

    def set_direction(self, pin, direction):
        if pin not in self.pins:
            self._export(pin)
        with open(f"/sys/class/gpio/gpio{pin}/direction", "w") as f:
            f.write(direction)
        # race with KeyboardInterrupt
        self.pins[pin] = direction

    def set_value(self, pin, value):
        logger.debug(f"{pin: 3} = {value}")
        if pin not in self.pins:
            self._export(pin)
        if self.pins[pin] == "in":
            if value == 0:
                direction = "low"
            elif value == 1:
                direction = "high"
            else:
                raise Exception(f"invalid pin value {value!r}")
            self.set_direction(pin, direction)
        else:
            with open(f"/sys/class/gpio/gpio{pin}/value", "w") as f:
                f.write(f"{value}")

    def get_value(self, pin):
        with open(f"/sys/class/gpio/gpio{pin}/value", "r") as f:
            return int(f.read().rstrip("\n"))

    def __exit__(self, *_exc_info):
        exc = None
        for pin in self.pins.copy().keys():
            try:
                self._unexport(pin)
            except Exception as e:
                logger.exception(f"can't unexport GPIO pin {pin}")
                exc = e
        del self.pins
        if exc:
            raise exc
