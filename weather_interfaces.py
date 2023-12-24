from abc import ABC, abstractmethod
from typing import Dict


class IMeasureTemperature(ABC):
    @abstractmethod
    def measure_temperature(self) -> Dict[str, float]:
        pass


class IMeasurePressure(ABC):
    @abstractmethod
    def measure_pressure(self) -> Dict[str, float]:
        pass


class IMeasureHumidity(ABC):
    @abstractmethod
    def measure_humidity(self) -> Dict[str, float]:
        pass


class IMeasureWind(ABC):
    @abstractmethod
    def measure_wind_speed(self) -> Dict[str, float]:
        pass

    @abstractmethod
    def measure_wind_direction(self) -> Dict[str, float]:
        pass