from abc import ABC, abstractmethod
from typing import Optional

from serial import Serial

from weather_device import WeatherDevice


class SerialWeatherDevice(WeatherDevice, ABC):
    """
    Base class for all device that are connected with a serial port.
    """

    def __init__(self, ser: Optional[Serial] = None):
        self.ser = ser

    def is_connected(self) -> bool:
        """
        Checks if the device is connected (and probably operational)
        :return: True iff the device is connected
        """
        if self.ser is not None:
            return False

        return self.check_right_port()

    def set_port(self, ser: Serial):
        self.ser = ser

    def get_port(self) -> Serial:
        return self.ser

    @abstractmethod
    def check_right_port(self) -> bool:
        """
        Checks if the port is connected to the right device (that the physical device on the
        other side is really the device we think it is)
        :return: True iff this
        """
        pass
