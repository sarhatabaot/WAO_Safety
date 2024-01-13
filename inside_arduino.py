import datetime
import logging
from typing import Optional, Union, List

from query_weather_arduino import ArduinoInterface
# from weather_measurement import WeatherMeasurement
# from weather_parameter import WeatherParameter
from stations import Station, Reading, Datum, SerialStation
from enum import Enum
from utils import cfg


class InsideArduinoDatum(str, Enum, Datum):
    TemperatureIn = "temperature_in",
    PressureIn = "pressure_in",
    VisibleLuxIn = "visible_lux_in",
    Presence = "presence",
    Flame = "flame",
    CO2 = "co2",
    RawH2 = "raw_h2",
    RawEthanol = "raw_ethanol",
    VOC = "voc",

    @classmethod
    def names(cls) -> List[str]:
        return list(cls.__members__.keys())

    
class InsideArduinoReading(Reading):
    def __init__(self):
        super().__init__()
        for name in InsideArduinoDatum.names():
            self.data[name] = None
            
    
class InsideArduino(SerialStation, Station):
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(self.name)
        try:
            super(SerialStation).__init__(name=self.name, logger=self.logger)
        except Exception as ex:
            self.logger.error(f"Cannot construct SerialStation for '{self.name}'")
            return

        config = cfg.get(f"stations.{self.name}")
        self.interval = config.data['interval'] if 'interval' in config.data else 60

    @staticmethod
    def get_correct_file() -> str:
        return "Indoor_multiQuery.ino"

    def datum_names(self) -> List[str]:
        return InsideArduinoDatum.names()

    def fetcher(self) -> None:
        reading = InsideArduinoReading()

        try:
            self._measure_pressure(reading)
            self._measure_temperature(reading)
            self._measure_gas(reading)
            self._measure_flame(reading)
            self._measure_presence(reading)
            self._measure_light(reading)
        except Exception as ex:
            # TODO: log
            return

        reading.tstamp = datetime.datetime.utcnow()
        self._readings.append(reading)
        if hasattr(self, 'saver'):
            self.saver(reading)

    def _measure_light(self, reading: InsideArduinoReading):
        response = self._send_and_parse_query("light", 0.08, "light (Lux): {f}")
        reading.data[InsideArduinoDatum.VisibleLuxIn] = response[0]

    def _measure_pressure(self, reading: InsideArduinoReading):
        response = self._send_and_parse_query("pressure", 0.1, "Pressure: {f}hPa")
        reading.data[InsideArduinoDatum.PressureIn] = response[0]

    def _measure_temperature(self, reading: InsideArduinoReading):
        response = self._send_and_parse_query("temp", 0.1, "Temperature: {f}°C")
        reading.data[InsideArduinoDatum.TemperatureIn] = response[0]

    def _measure_gas(self, reading: InsideArduinoReading):
        response = self._send_and_parse_query("gas", 0.07,
                                              "CO2: {i} ppm\tTVOC: {i} ppb\tRaw H2: {i} \tRaw Ethanol: {i}")
        reading.data[InsideArduinoDatum.CO2] = response[0]
        reading.data[InsideArduinoDatum.VOC] = response[1]
        reading.data[InsideArduinoDatum.RawH2] = response[2]
        reading.data[InsideArduinoDatum.RawEthanol] = response[3]

    def _measure_flame(self, reading: InsideArduinoReading):
        response = self._send_and_parse_query("flame", 0.05, "IR reading: {i}")
        reading.data[InsideArduinoDatum.Flame] = response[0]

    def _measure_presence(self, reading: InsideArduinoReading):
        response = self._send_and_parse_query("presence", 0.05, "Presence: {i}")
        reading.data[InsideArduinoDatum.Presence] = response[0]
