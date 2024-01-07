from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict

from weather_parameter import WeatherParameter
from weather_measurement import WeatherMeasurement
from weather_device import WeatherDevice


class CalculationDevice(WeatherDevice, ABC):
    """
    A CalculationDevice is a device that does not make
    measurements from a physical device but calculates some values
    """

    @abstractmethod
    def _calculate(self) -> Dict[WeatherParameter, float]:
        pass

    def is_connected(self) -> bool:
        return True

    def measure_parameter(self, parameter: WeatherParameter):
        """
        :param parameter: parameter to measure
        :return:
        """
        if not self.can_measure(parameter):
            return None

        return self._calculate()[parameter]

    def measure_all(self):
        data = self._calculate()

        timestamp = datetime.now()

        return WeatherMeasurement(data, timestamp)
