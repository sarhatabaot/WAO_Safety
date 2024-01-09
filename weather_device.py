from abc import ABC, abstractmethod
from typing import List, Optional, Union

from weather_measurement import WeatherMeasurement
from weather_parameter import WeatherParameter


class WeatherDevice(ABC):
    """
    Base class for all weather devices. A weather device is any piece of physical
    equipment, external source or something else that returns data about the weather.
    """

    @abstractmethod
    def is_connected(self) -> bool:
        pass

    @abstractmethod
    def list_measurements(self) -> List[WeatherParameter]:
        """
        List the parameters the device can measure.
        :return: list of parameters
        """
        pass

    def can_measure(self,  parameter: WeatherParameter) -> bool:
        """
        Checks if the device can measure the parameters
        :param parameter: requested weather parameter
        :return: True iff the device can measure the parameter
        """
        all_measurements = self.list_measurements()

        return parameter in all_measurements

    @abstractmethod
    def measure_parameter(self, parameter: WeatherParameter) -> Optional[Union[int, float]]:
        """
        Measure the value of the parameter
        :param parameter: weather parameter to measure
        :return: value of measurements
        """
        pass

    @abstractmethod
    def measure_all(self) -> Optional[WeatherMeasurement]:
        """
        Measures all parameters the device can measure.
        :return: WeatherMeasurement object with all parameters values and a timestamp
        """
        pass
