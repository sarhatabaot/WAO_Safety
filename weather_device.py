from abc import ABC, abstractmethod
from typing import List, Optional, Union
from enum import Enum

from weather_measurement import WeatherMeasurement
from weather_parameter import WeatherParameter


class DeviceName(str, Enum):
    ARDUINO_IN = "arduino_in"
    ARDUINO_OUT = "arduino_out"
    DAVIS_VANTAGE = "davis_vantage"


class DeviceType(str, Enum):
    SERIAL = "serial"
    OTHER = "other"


def get_device_type(device_name: DeviceName) -> DeviceType:
    if device_name in [DeviceName.DAVIS_VANTAGE, DeviceName.ARDUINO_IN, DeviceName.ARDUINO_OUT]:
        return DeviceType.SERIAL
    else:
        return DeviceType.OTHER


class WeatherDevice(ABC):
    @abstractmethod
    def is_connected(self) -> bool:
        pass

    @abstractmethod
    def list_measurements(self) -> List[WeatherParameter]:
        pass

    def can_measure(self,  parameter: WeatherParameter) -> bool:
        all_measurements = self.list_measurements()

        return parameter in all_measurements

    @abstractmethod
    def measure_parameter(self, parameter: WeatherParameter) -> Optional[Union[int, float]]:
        """
        :param parameter: parameter to measure
        :return:
        """
        pass

    @abstractmethod
    def measure_all(self) -> Optional[WeatherMeasurement]:
        pass
