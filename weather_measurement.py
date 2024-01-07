from datetime import datetime
from typing import Dict, Union

from weather_parameter import WeatherParameter


class WeatherMeasurement:
    def __init__(self, measured_parameters: Dict[WeatherParameter, Union[int, float]], timestamp: datetime = None):
        self.measured_parameters: Dict = measured_parameters

        if timestamp is None:
            self.timestamp = datetime.now()
        else:
            self.timestamp = timestamp

    def get_timestamp(self) -> datetime:
        return self.timestamp

    def list_parameters(self):
        return list(self.measured_parameters.keys())

    def get_parameter(self, parameter: WeatherParameter):
        return self.measured_parameters.get(parameter)
    
    def __str__(self) -> str:
        txt = "Weather Measurement\n"
        for param, val in self.measured_parameters.items():
            txt += f"({param}: {val})\n"

        return txt
        
    def get_all_parameters(self):
        return self.measured_parameters
