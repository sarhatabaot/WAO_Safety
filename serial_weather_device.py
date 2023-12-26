from abc import ABC, abstractmethod
from typing import Optional
import tomlkit

from serial import Serial
import serial.tools.list_ports

from weather_device import WeatherDevice, DeviceName
import vantage_pro2
import inside_arduino
import outside_arduino


class SerialWeatherDevice(WeatherDevice, ABC):
    _serial_ports = serial.tools.list_ports.comports()
    _free_ports = {ser_port.device: True for ser_port in _serial_ports}

    _CONFIG_PATH = "serial_config.toml"

    def __init__(self, ser: Optional[Serial] = None):
        self.ser = ser

    def is_connected(self) -> bool:
        if self.ser is not None:
            return False

        return self.check_right_port()

    def set_port(self, ser: Serial):
        self.ser = ser

    def get_port(self) -> Serial:
        return self.ser

    @abstractmethod
    def check_right_port(self) -> bool:
        pass

    @staticmethod
    def _get_config_table_name(device: DeviceName) -> str:
        return device.value

    @staticmethod
    def connect_device(device_name: DeviceName):
        config_name = SerialWeatherDevice._get_config_table_name(device_name)

        print(f"Trying to connect {device_name}")

        with open(SerialWeatherDevice._CONFIG_PATH, "r") as f:
            doc = tomlkit.load(f)
            default_port = doc[config_name]["com_port"]
            baud_rate = doc[config_name]["baud_rate"]

        print(f"port: {default_port}")
        print(f"baud rate: {baud_rate}")

        print(SerialWeatherDevice._free_ports)

        if device_name == DeviceName.DAVIS_VANTAGE:
            device = vantage_pro2.VantagePro2()
        elif device_name == DeviceName.ARDUINO_IN:
            device = inside_arduino.InsideArduino()
        elif device_name == DeviceName.ARDUINO_OUT:
            device = outside_arduino.OutsideArduino()
        else:
            return None

        # there is a default port
        if device_name != "":
            # default port available
            if SerialWeatherDevice._free_ports.get(default_port, False):
                print("default port is free")
                ser = serial.Serial(default_port, baud_rate)
                device.set_port(ser)

                # device connected
                if device.check_right_port():
                    return device

        # look for other port
        for other_port in SerialWeatherDevice._free_ports:
            # port is available
            if other_port != default_port and SerialWeatherDevice._free_ports[other_port]:
                ser = serial.Serial(default_port, baud_rate)
                device.set_port(ser)

                # device connected
                if device.check_right_port():
                    return device

        # can't connect device
        return None
