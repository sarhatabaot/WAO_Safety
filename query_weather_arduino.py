import time
from abc import ABC, abstractmethod
from typing import Tuple, Union

from serial_weather_device import SerialWeatherDevice
from parser import Parser


class QueryWeatherArduino(SerialWeatherDevice, ABC):
    def __init__(self, ser):
        super().__init__(ser)

    def _query(self, param_name: str, wait: float) -> str:
        request_txt = f"{param_name}?\r\n"
        self.ser.write(request_txt.encode("utf-8"))
        time.sleep(wait)

        response_txt =  self.ser.readline().decode("utf-8")

        while response_txt == request_txt:
            response_txt =  self.ser.readline().decode("utf-8")

        return response_txt

    def _send_and_parse_query(self, parma_name, wait: float, format_str: str) -> Tuple[Union[int, float]]:
        response = self._query(parma_name, wait)
        print("_send_and_parse_query!!!!")
        print(f"!!!! format   : {format_str}|")
        print(f"!!!! response : {response}|")

        if "TSL" in format_str:
            print("debug here")

        return Parser.parse(format_str, response)

    @abstractmethod
    def get_correct_file(self) -> str:
        pass

    def check_right_port(self) -> bool:
        print("checking if arduino is connected correctly")
        response = self._query("id", 0.5)
        print(response)

        return self.get_correct_file() in response

