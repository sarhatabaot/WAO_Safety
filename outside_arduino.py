from typing import Optional, Union, List

from serial import Serial

from query_weather_arduino import QueryWeatherArduino
from weather_measurement import WeatherMeasurement
from weather_parameter import WeatherParameter


class OutsideArduino(QueryWeatherArduino):
    def __init__(self, serial_port: Optional[Serial] = None):
        super().__init__(serial_port)

    def list_measurements(self) -> List[WeatherParameter]:
        return [WeatherParameter.TEMPERATURE_OUT,
                WeatherParameter.HUMIDITY_OUT,
                WeatherParameter.PRESSURE_OUT,
                WeatherParameter.DEW_POINT,
                WeatherParameter.VISIBLE_LUX_OUT,
                WeatherParameter.IR_LUMINOSITY,
                WeatherParameter.WIND_SPEED,
                WeatherParameter.WIND_DIRECTION]

    def measure_parameter(self, parameter: WeatherParameter) -> Optional[Union[int, float]]:
        if not self.can_measure(parameter):
            return None

        if parameter in [WeatherParameter.WIND_SPEED, WeatherParameter.WIND_DIRECTION]:
            return self._measure_wind()[parameter]
        elif parameter in [WeatherParameter.VISIBLE_LUX_OUT, WeatherParameter.IR_LUMINOSITY]:
            return self._measure_light()[parameter]
        elif parameter in [WeatherParameter.TEMPERATURE_OUT, WeatherParameter.PRESSURE_OUT, WeatherParameter.DEW_POINT]:
            return self._measure_pressure_humidity_temperature()[parameter]
        else:
            return None

    def measure_all(self) -> Optional[WeatherMeasurement]:
        data = dict()
        data.update(self._measure_wind())
        data.update(self._measure_light())
        data.update(self._measure_pressure_humidity_temperature())

        return WeatherMeasurement(data)

    def _measure_wind(self):
        wind_results = self._send_and_parse_query("wind", 0.05, "v= {f} m/s dir. {f}°")

        return {WeatherParameter.WIND_SPEED: wind_results[0],
                WeatherParameter.WIND_DIRECTION: wind_results[1]}

    def _measure_light(self):
        light_results = self._send_and_parse_query("light", 0.08,
                                                   "TSL vis(Lux) IR(luminosity): {i} {f}")

        return {WeatherParameter.VISIBLE_LUX_OUT: light_results[0],
                WeatherParameter.IR_LUMINOSITY: light_results[1]}

    def _measure_pressure_humidity_temperature(self):
        results = self._send_and_parse_query("pht", 0.08,
                                             "P: {f}hPa T: {f}°C RH: {f}% comp RH: {f}% dew point: {f}°C")

        return {WeatherParameter.PRESSURE_OUT: results[0],
                WeatherParameter.TEMPERATURE_OUT: results[1],
                WeatherParameter.HUMIDITY_OUT: results[2],
                WeatherParameter.DEW_POINT: results[4]}

    def get_correct_file(self) -> str:
        return "Outdoor_multiQuery.ino"
