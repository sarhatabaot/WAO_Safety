import datetime
import logging
from typing import List

from query_weather_arduino import ArduinoInterface
# from weather_measurement import WeatherMeasurement
# from weather_parameter import WeatherParameter
from stations import Station, Reading, SerialStation
from enum import Enum
from utils import cfg


class InsideArduinoDatum(str, Enum):
    TemperatureIn = "temperature_in",
    PressureIn = "pressure_in",
    VisibleLuxIn = "visible_lux_in",
    Presence = "presence",
    Flame = "flame",
    CO2 = "co2",
    RawH2 = "raw_h2",
    RawEthanol = "raw_ethanol",
    VOC = "voc",

    
class InsideArduinoReading(Reading):
    def __init__(self):
        super().__init__()
        for name in [item.value for item in InsideArduinoDatum]:
            self.datums[name] = None
            
    
class InsideArduino(SerialStation):
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(self.name)
        try:
            super(SerialStation).__init__(name=self.name, logger=self.logger)
        except Exception as ex:
            self.logger.error(f"Cannot construct SerialStation for '{self.name}'")
            return

        config = cfg.get(f"stations.{self.name}")
        self.interval = config.datums['interval'] if 'interval' in config.datums else 60

    @staticmethod
    def get_correct_file() -> str:
        return "Indoor_multiQuery.ino"

    def datums(self) -> List[str]:
        return [item.value for item in InsideArduinoDatum]

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
        reading.datums[InsideArduinoDatum.VisibleLuxIn] = response[0]

    def _measure_pressure(self, reading: InsideArduinoReading):
        response = self._send_and_parse_query("pressure", 0.1, "Pressure: {f}hPa")
        reading.datums[InsideArduinoDatum.PressureIn] = response[0]

    def _measure_temperature(self, reading: InsideArduinoReading):
        response = self._send_and_parse_query("temp", 0.1, "Temperature: {f}°C")
        reading.datums[InsideArduinoDatum.TemperatureIn] = response[0]

    def _measure_gas(self, reading: InsideArduinoReading):
        response = self._send_and_parse_query("gas", 0.07,
                                              "CO2: {i} ppm\tTVOC: {i} ppb\tRaw H2: {i} \tRaw Ethanol: {i}")
        reading.datums[InsideArduinoDatum.CO2] = response[0]
        reading.datums[InsideArduinoDatum.VOC] = response[1]
        reading.datums[InsideArduinoDatum.RawH2] = response[2]
        reading.datums[InsideArduinoDatum.RawEthanol] = response[3]

    def _measure_flame(self, reading: InsideArduinoReading):
        response = self._send_and_parse_query("flame", 0.05, "IR reading: {i}")
        reading.datums[InsideArduinoDatum.Flame] = response[0]

    def _measure_presence(self, reading: InsideArduinoReading):
        response = self._send_and_parse_query("presence", 0.05, "Presence: {i}")
        reading.datums[InsideArduinoDatum.Presence] = response[0]
