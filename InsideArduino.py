import serial
import tomlkit
from typing import Tuple
from collections import namedtuple
import datetime
from dataclasses import dataclass

CONFIG_PATH = "/home/ocs/python/security/WeatherSafety/config.toml"


@dataclass
class GasMeasurement:
    co2: int
    voc: int
    raw_h2: int
    raw_ethanol: int


@dataclass
class InsideArduinoMeasurement:
    timestamp: datetime.datetime
    pressure: float
    temperature: float
    co2: int
    voc: int
    raw_h2: int
    raw_ethanol: int
    flame: int
    presence: bool


class InsideArduino:
    def __init__(self):
        with open(CONFIG_PATH, "r") as f:
            doc = tomlkit.load(f)

            com_port = doc["OutsideArduino"]["com_port"]
            baud_rate = doc["OutsideArduino"]["baud_rate"]

            self.ser = serial.Serial(com_port, baud_rate)

    def _query(self, param_name: str):
        self.ser.write("{param_name}?".encode("utf-8"))

    @staticmethod
    def _parse_pressure(response: bytes) -> float:
        pressure_start_index = response.index("Pressure: ".encode("utf-8")) + len("Pressure: ".encode("utf-8"))
        pressure_end_index = response.index("hPa".encode("utf-8"))

        return float(response[pressure_start_index: pressure_end_index])

    @staticmethod
    def _parse_temperature(response: bytes) -> float:
        temperature_start_index = response.index("Temperature: ".encode("utf-8")) + len("Temperature: ".encode("utf-8"))
        temperature_end_index = response.index("°C".encode("utf-8"))

        return float(response[temperature_start_index: temperature_end_index])

    @staticmethod
    def _parse_gas(response: bytes) -> Tuple[int, int, int, int]:
        co2_start_index = response.index("CO2: ".encode("utf-8")) + len("CO2: ".encode("utf-8"))
        co2_end_index = response.index(" ppm\tTVOC: ".encode("utf-8"))

        voc_start_index = co2_end_index + len(" ppm\tTVOC: ".encode("utf-8"))
        voc_end_index = response.index(" ppb\tRaw H2: ".encode("utf-8"))

        raw_h2_start_index = voc_end_index + len(" ppb\tRaw H2: ".encode("utf-8"))
        raw_h2_end_index = response.index(" \tRaw Ethanol: ".encode("utf-8"))

        raw_ethanol_start_index = raw_h2_end_index + len(" \tRaw Ethanol: ".encode("utf-8"))
        raw_ethanol_end_index = response.index("\n".encode("utf-8"))

        co2 = int(response[co2_start_index: co2_end_index])
        voc = int(response[voc_start_index: voc_end_index])
        raw_h2 = int(response[raw_h2_start_index: raw_h2_end_index])
        raw_ethanol = int(response[raw_ethanol_start_index: raw_ethanol_end_index])

        return co2, voc, raw_h2, raw_ethanol

    @staticmethod
    def _parse_flame(response: bytes) -> int:
        ir_start_index = response.index("IR reading: ".encode("utf-8")) + len("IR reading: ".encode("utf-8"))
        ir_end_index = response.index("\n".encode("utf-8"))
        return int(response[ir_start_index: ir_end_index])

    @staticmethod
    def _parse_presence(response: bytes) -> bool:
        presence_start = response.index("Presence: ".encode("utf-8"))
        presence_end = response.index("\n".encode("utf-8")) - 1

        return bool(int(response[presence_start: presence_end]))

    def _measure_pressure(self) -> float:
        self._query("pressure?")
        response = self.ser.readline()

        return InsideArduino._parse_pressure(response)

    def _measure_temperature(self) -> float:
        self._query("temp?")
        response = self.ser.readline()

        return InsideArduino._parse_temperature(response)

    def _measure_gas(self) -> GasMeasurement:
        self._query("gas?")
        response = self.ser.readline()

        return GasMeasurement(*InsideArduino._parse_gas(response))

    def _measure_flame(self) -> int:
        self._query("flame?")
        response = self.ser.readline()

        return InsideArduino._parse_flame(response)

    def _measure_presence(self) -> bool:
        self._query("presence?")
        response = self.ser.readline()

        return InsideArduino._parse_presence(response)

    def measure(self) -> InsideArduinoMeasurement:
        timestamp = datetime.datetime.now()
        pressure = self._measure_pressure()
        temperature = self._measure_temperature()
        gas = self._measure_gas()
        flame = self._measure_flame()
        presence = self._measure_presence()

        return InsideArduinoMeasurement(timestamp=timestamp,
                                        pressure=pressure,
                                        temperature=temperature,
                                        co2=gas.co2,
                                        voc=gas.voc,
                                        raw_h2=gas.raw_h2,
                                        raw_ethanol=gas.raw_ethanol,
                                        flame=flame,
                                        presence=presence)
