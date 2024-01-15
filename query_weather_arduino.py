import time
from abc import ABC, abstractmethod
from typing import Tuple, Union

from serial_weather_device import SerialWeatherDevice
from my_parser import Parser
from stations import SerialStation


# class ArduinoInterface(SerialWeatherDevice, ABC):
class ArduinoInterface(SerialStation, ABC):
    """
    This is a base class for several similar Arduino devices.
    All devices that inherit from this class are devices with this API:

    PC: <measurement name>?
    ARDUINO: <some text><value 1><some text><value 2><some text>
    """
    def __init__(self, ser):
        super().__init__(ser)

    def _query(self, param_name: str, wait: float) -> str:
        """
        This function sends a request from the arduino, sleeps some time and
        then reads the response
        :param param_name:
        :param wait: time to sleep
        :return: arduino response
        """
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()

        request_txt = f"{param_name}?\r\n"

        self.ser.write(request_txt.encode("utf-8"))
        time.sleep(wait)

        response_txt = self.ser.readline().decode("utf-8")

        # TODO: Find reason for echo
        while response_txt == request_txt:
            response_txt = self.ser.readline().decode("utf-8")

        return response_txt

    def _send_and_parse_query(self, param_name, wait: float, format_str: str) -> Tuple[Union[int, float]]:
        """
        Sends a request and returns the values in the request.
        All the arduino responses are in the format of: <some text><value><some text><value 2><some text>.
        :param param_name: name of query
        :param wait: time to sleep
        :param format_str: format of the response. See Parser documentation for details.
        :return: A tuple contaminating the values from the response
        """
        response = self._query(param_name, wait)

        return Parser.parse(format_str, response)

    @abstractmethod
    def get_correct_file(self) -> str:
        """
        :return: the name of the file where the arduino code is written.
        Different types of arduinos have different file names.
        """
        pass

    def check_right_port(self) -> bool:
        """
        All arduinos have an "id?" command that returns compilation details, including their file name.
        I check if the right filename is in the response
        :return: True iff the right arduino is connected
        """
        response = self._query("id", 0.5)

        return self.get_correct_file() in response

