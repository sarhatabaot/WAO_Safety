from abc import ABC, abstractmethod
from typing import List, Optional, Union

from weather_measurement import WeatherMeasurement
from weather_parameter import WeatherParameter


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
