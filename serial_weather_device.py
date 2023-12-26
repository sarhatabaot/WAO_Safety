from abc import ABC, abstractmethod
from typing import Optional
import tomlkit

from serial import Serial
import serial.tools.list_ports

from weather_device import WeatherDevice, DeviceName


class SerialWeatherDevice(WeatherDevice, ABC):
    _serial_ports = serial.tools.list_ports.comports()
    _free_ports = {ser_port.device: True for ser_port in _serial_ports}

    _CONFIG_PATH = "serial_config.toml"

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

    @staticmethod
    def _get_config_table_name(device: DeviceName) -> str:
        return device.value
