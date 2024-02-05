import datetime
import logging
from typing import List
import serial

from station import SerialStation
from config.config import make_cfg
from init_log import init_log
from arduino import Arduino
from db_access import make_db_manager, DbManager
from utils import InsideArduinoDatum, InsideArduinoReading


class InsideArduino(SerialStation, Arduino):

    db_manager: DbManager

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(self.name)
        init_log(self.logger)

        try:
            super().__init__(name=self.name)
        except Exception as ex:
            self.logger.error(f"Cannot construct SerialStation for '{self.name}'", exc_info=ex)
            return

        cfg = make_cfg()
        self.interval = cfg.station_settings[self.name].interval
        self.db_manager = make_db_manager()

    def get_correct_file(self) -> str:
        return "Indoor_multiQuery.ino"

    def datums(self) -> List[str]:
        return [item.value for item in InsideArduinoDatum]

    def fetcher(self) -> None:
        # print(f"{self.name} fetcher is bypassed")
        # return

        try:
            self.ser = serial.Serial(port=self.port, baudrate=self.baud,
                                     timeout=self.timeout, write_timeout=self.write_timeout)
        except serial.serialutil.SerialException as ex:
            self.logger.error(f"Could not open '{self.port}", exc_info=ex)
            self.ser.close()
            return

        reading = InsideArduinoReading()

        try:
            self.get_pressure(reading)
            self.get_temperature(reading)
            self.get_gas(reading)
            self.get_flame(reading)
            self.get_presence(reading)
            self.get_light(reading)
            self.ser.close()
        except Exception as ex:
            self.logger.error(f"fetcher: Failed", exc_info=ex)
            self.ser.close()
            raise

        reading.tstamp = datetime.datetime.utcnow()
        self.logger.debug(f"reading: {reading.__dict__}")
        with self.lock:
            self.readings.push(reading)
        # if hasattr(self, 'saver'):
        #     self.saver(reading)

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
        if reading is None:
            return

        response = self.query("pressure", 0.1, "Pressure: {f}hPa")
        reading.datums[InsideArduinoDatum.PressureIn] = response[0]

    def get_temperature(self, reading: InsideArduinoReading):
        response = self.query("temp", 0.1, "Temperature: {f}°C")
        reading.datums[InsideArduinoDatum.TemperatureIn] = response[0]

    def get_gas(self, reading: InsideArduinoReading):
        if reading is None:
            return

        response = self.query("gas", 0.07, "CO2: {i} ppm\tTVOC: {i} ppb\tRaw H2: {i} \tRaw Ethanol: {i}")
        reading.datums[InsideArduinoDatum.CO2] = response[0]
        reading.datums[InsideArduinoDatum.VOC] = response[1]
        reading.datums[InsideArduinoDatum.RawH2] = response[2]
        reading.datums[InsideArduinoDatum.RawEthanol] = response[3]

    def get_flame(self, reading: InsideArduinoReading):
        if reading is None:
            return

        response = self.query("flame", 0.05, "IR reading: {i}")
        reading.datums[InsideArduinoDatum.Flame] = response[0]

    def get_presence(self, reading: InsideArduinoReading):
        response = self.query("presence", 0.05, "Presence: {i}")
        reading.datums[InsideArduinoDatum.Presence] = response[0]
