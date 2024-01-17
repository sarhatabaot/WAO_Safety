import datetime
import logging
from typing import List

from station import Reading, SerialStation
from enum import Enum
from utils import cfg, SingletonFactory, init_log
from arduino import Arduino


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
    
    @classmethod
    def names(cls) -> list:
        return [item.value for item in cls]

    
class InsideArduinoReading(Reading):
    def __init__(self):
        super().__init__()
        for name in InsideArduinoDatum.names():
            self.datums[name] = None
            
    
class InsideArduino(SerialStation, Arduino):
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(self.name)
        init_log(self.logger)

        try:
            super().__init__(name=self.name)
        except Exception as ex:
            self.logger.error(f"Cannot construct SerialStation for '{self.name}'", exc_info=ex)
            return

        config = cfg.get(f"stations.{self.name}")
        self.interval = config['interval'] if 'interval' in config else 60

        from db_access import DbManager
        self.db_manager = SingletonFactory.get_instance(DbManager)
        self.db_manager.connect()
        self.db_manager.open_session()

    def get_correct_file(self) -> str:
        return "Indoor_multiQuery.ino"

    def datums(self) -> List[str]:
        return [item.value for item in InsideArduinoDatum]

    def fetcher(self) -> None:
        reading = InsideArduinoReading()

        try:
            self.get_pressure(reading)
            self.get_temperature(reading)
            self.get_gas(reading)
            self.get_flame(reading)
            self.get_presence(reading)
            self.get_light(reading)
        except Exception as ex:
            self.logger.error(f"fetcher: Failed", exc_info=ex)
            return

        reading.tstamp = datetime.datetime.utcnow()
        self.readings.push(reading)
        if hasattr(self, 'saver'):
            self.saver(reading)

    def saver(self, reading: InsideArduinoReading) -> None:
        from db_access import ArduinoInDbClass

        arduino_in = ArduinoInDbClass(
            presence=reading.datums[InsideArduinoDatum.Presence],
            temp_in=reading.datums[InsideArduinoDatum.TemperatureIn],
            pressure_in=reading.datums[InsideArduinoDatum.PressureIn],
            visible_lux_in=reading.datums[InsideArduinoDatum.VisibleLuxIn],
            flame=reading.datums[InsideArduinoDatum.Flame],
            co2=reading.datums[InsideArduinoDatum.CO2],
            voc=reading.datums[InsideArduinoDatum.VOC],
            raw_h2=reading.datums[InsideArduinoDatum.RawH2],
            raw_ethanol=reading.datums[InsideArduinoDatum.RawEthanol],
            tstamp=reading.tstamp,
        )

        self.db_manager.session.add(arduino_in)
        self.db_manager.session.commit()

    def get_light(self, reading: InsideArduinoReading):
        response = self.query("light", 0.08, "light (Lux): {f}")
        reading.datums[InsideArduinoDatum.VisibleLuxIn] = response[0]

    def get_pressure(self, reading: InsideArduinoReading):
        response = self.query("pressure", 0.1, "Pressure: {f}hPa")
        reading.datums[InsideArduinoDatum.PressureIn] = response[0]

    def get_temperature(self, reading: InsideArduinoReading):
        response = self.query("temp", 0.1, "Temperature: {f}°C")
        reading.datums[InsideArduinoDatum.TemperatureIn] = response[0]

    def get_gas(self, reading: InsideArduinoReading):
        response = self.query("gas", 0.07, "CO2: {i} ppm\tTVOC: {i} ppb\tRaw H2: {i} \tRaw Ethanol: {i}")
        reading.datums[InsideArduinoDatum.CO2] = response[0]
        reading.datums[InsideArduinoDatum.VOC] = response[1]
        reading.datums[InsideArduinoDatum.RawH2] = response[2]
        reading.datums[InsideArduinoDatum.RawEthanol] = response[3]

    def get_flame(self, reading: InsideArduinoReading):
        response = self.query("flame", 0.05, "IR reading: {i}")
        reading.datums[InsideArduinoDatum.Flame] = response[0]

    def get_presence(self, reading: InsideArduinoReading):
        response = self.query("presence", 0.05, "Presence: {i}")
        reading.datums[InsideArduinoDatum.Presence] = response[0]
