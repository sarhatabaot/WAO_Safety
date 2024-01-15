import datetime
from typing import Optional, Union, List

from serial import Serial

from query_weather_arduino import ArduinoInterface
from weather_measurement import WeatherMeasurement
from weather_parameter import WeatherParameter

from stations import Station, Reading, Datum, SerialStation
from enum import Enum
import logging
from utils import cfg


class OutsideArduinoDatum(str, Enum, Datum):
    TemperatureOut = "temperature_out",
    HumidityOut = "humidity_out",
    PressureOut = "pressure_out",
    DewPoint = "dew_point",
    VisibleLuxOut = "visible_lux_out",
    IrLuminosity = "ir_luminosity",
    WindSpeed = "wind_speed",
    WindDirection = "wind_direction",


class OutsideArduinoReading(Reading):
    def __init__(self):
        for name in OutsideArduinoDatum.names():
            self.datums[name] = None


class OutsideArduino(SerialStation, Station):
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(self.name)
        super(SerialStation, self).__init__(name=self.name, logger=self.logger)

        config = cfg.get(f"stations.{self.name}")
        self.interval = config.datums['interval'] if 'interval' in config.datums else 60

    @classmethod
    def datums(cls) -> List[str]:
        return [item.value for item in OutsideArduinoDatum]

    def fetcher(self) -> None:
        reading: OutsideArduinoReading = OutsideArduinoReading()

        try:
            self._measure_wind(reading)
            self._measure_light(reading)
            self._measure_pressure_humidity_temperature(reading)
        except Exception as ex:
            # TODO: log
            return

        reading.tstamp = datetime.datetime.utcnow()
        self._readings.append(reading)
        if hasattr(self, 'saver'):
            self.saver(reading)

    def _measure_wind(self, reading: OutsideArduinoReading):
        wind_results = self._send_and_parse_query("wind", 0.05, "v={f} m/s  dir. {f}°")

        reading.datums[OutsideArduinoDatum.WindSpeed] = wind_results[0]
        reading.datums[OutsideArduinoDatum.WindDirection] = wind_results[1]

    def _measure_light(self, reading: OutsideArduinoReading):
        light_results = self._send_and_parse_query("light", 0.08, "TSL vis(Lux) IR(luminosity): {i} {i}")

        reading.datums[OutsideArduinoDatum.VisibleLuxOut] = light_results[0]
        reading.datums[OutsideArduinoDatum.IrLuminosity] = light_results[1]

    def _measure_pressure_humidity_temperature(self, reading: OutsideArduinoReading):
        results = self._send_and_parse_query("pht", 0.08, "P:{f}hPa T:{f}°C RH:{f}% comp RH:{f}% dew point:{f}°C")

        reading.datums[OutsideArduinoDatum.PressureOut] = results[0]
        reading.datums[OutsideArduinoDatum.TemperatureOut] = results[1]
        reading.datums[OutsideArduinoDatum.HumidityOut] = results[2]
        reading.datums[OutsideArduinoDatum.DewPoint] = results[3]

    def get_correct_file(self) -> str:
        return "Outdoor_multiQuery.ino"
