import time
from abc import ABC, abstractmethod
from typing import Tuple, Union

from serial_weather_device import SerialWeatherDevice
from parser import Parser


class QueryWeatherArduino(SerialWeatherDevice, ABC):
    def __init__(self, ser):
        super().__init__(ser)

    def _query(self, param_name: str, wait: float) -> str:
        self.ser.write(f"{param_name}?\r\n".encode("utf-8"))
        time.sleep(wait)
        return self.ser.readline().decode("utf-8")

    def _send_and_parse_query(self, parma_name, wait: float, format_str: str) -> Tuple[Union[int, float]]:
        response = self._query(parma_name, wait)
        return Parser.parse(format_str, response)

    @abstractmethod
    def get_correct_file(self) -> str:
        pass

    def check_right_port(self) -> bool:
        response = self._query("id")
        return self.get_correct_file() in response

