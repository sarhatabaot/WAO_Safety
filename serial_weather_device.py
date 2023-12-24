from abc import ABC, abstractmethod
from typing import Optional

from serial import Serial

from weather_device import WeatherDevice


class SerialWeatherDevice(WeatherDevice, ABC):
    def __init__(self, ser: Optional[Serial] = None):
        self.ser = ser

    def is_connected(self) -> bool:
        if self.ser is not None:
            return False

        return self.check_right_port()

    def set_port(self, ser: Serial):
        self.ser = ser

    def get_port(self) -> Serial:
        return self.ser

    @abstractmethod
    def check_right_port(self) -> bool:
        pass
