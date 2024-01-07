from typing import Optional, Union, List

from query_weather_arduino import QueryWeatherArduino
from weather_measurement import WeatherMeasurement
from weather_parameter import WeatherParameter


class InsideArduino(QueryWeatherArduino):
    def __init__(self, ser=None):
        super().__init__(ser)

    def get_correct_file(self) -> str:
        return "Indoor_multiQuery.ino"

    def list_measurements(self) -> List[WeatherParameter]:
        return [WeatherParameter.TEMPERATURE_IN,
                WeatherParameter.PRESSURE_IN,
                WeatherParameter.VISIBLE_LUX_IN,
                WeatherParameter.PRESENCE,
                WeatherParameter.FLAME,
                WeatherParameter.CO2,
                WeatherParameter.VOC,
                WeatherParameter.RAW_H2,
                WeatherParameter.RAW_ETHANOL]

    def measure_parameter(self, parameter: WeatherParameter) -> Optional[Union[int, float]]:
        if not self.can_measure(parameter):
            return None

    def measure_all(self) -> Optional[WeatherMeasurement]:
        data = dict()
        data.update(self._measure_pressure())
        data.update(self._measure_temperature())
        data.update(self._measure_gas())
        data.update(self._measure_flame())
        data.update(self._measure_presence())
        data.update(self._measure_light())

        return WeatherMeasurement(data)

    def _measure_light(self):
        response = self._send_and_parse_query("light", 0.08, "light (Lux): {f}")

        return {WeatherParameter.VISIBLE_LUX_IN: response[0]}

    def _measure_pressure(self):
        response = self._send_and_parse_query("pressure", 0.1, "Pressure: {f}hPa")

        return {WeatherParameter.PRESSURE_IN: response[0]}

    def _measure_temperature(self):
        response = self._send_and_parse_query("temp", 0.1, "Temperature: {f}°C")

        return {WeatherParameter.TEMPERATURE_IN: response[0]}

    def _measure_gas(self):
        response = self._send_and_parse_query("gas", 0.07,
                                              "CO2: {i} ppm\tTVOC: {i} ppb\tRaw H2: {i} \tRaw Ethanol: {i}")

        return {WeatherParameter.CO2: response[0],
                WeatherParameter.VOC: response[1],
                WeatherParameter.RAW_H2: response[2],
                WeatherParameter.RAW_ETHANOL: response[3]}

    def _measure_flame(self):
        response = self._send_and_parse_query("flame", 0.05, "IR reading: {i}")

        return {WeatherParameter.FLAME: response[0]}

    def _measure_presence(self):
        response = self._send_and_parse_query("presence", 0.05, "Presence: {i}")

        return {WeatherParameter.PRESENCE: response[0]}
