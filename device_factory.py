import os.path
from typing import Optional
from enum import Enum

from device_name import DeviceName
from serial_weather_device import SerialWeatherDevice

from vantage_pro2 import VantagePro2
from inside_arduino import InsideArduino
from outside_arduino import OutsideArduino
from SunElevationDevice import SunElevationDevice

import tomlkit
import serial
import serial.tools.list_ports

from config.config import cfg


class DeviceType(str, Enum):
    SERIAL = "serial"
    CALCULATION = "calculation"
    OTHER = "other"


class DeviceFactory:
    """
    This class is supposed to read all the config files and create a
    functioning device instance, that can be accessed to make measurements.

    This is the advised way to create devices.
    """
    _serial_ports = serial.tools.list_ports.comports()
    _free_serial_ports = {ser_port.device: True for ser_port in _serial_ports}

    CONFIG_FOLDER = "device_config"

    SERIAL_CONFIG_PATH = os.path.join(CONFIG_FOLDER, "serial_config.toml")
    CALCULATION_CONFIG_PATH = os.path.join(CONFIG_FOLDER, "calculation_config.toml")
    ACTIVE_DEVICES_CONFIG_PATH = os.path.join(CONFIG_FOLDER, "active_devices.toml")

    SERIAL_DEVICES = [DeviceName.DAVIS_VANTAGE, DeviceName.ARDUINO_IN, DeviceName.ARDUINO_OUT]
    CALCULATION_DEVICES = [DeviceName.SUN_ELEVATION_CALCULATOR]

    @staticmethod
    def get_device_type(device_name: DeviceName) -> DeviceType:
        if device_name in DeviceFactory.SERIAL_DEVICES:
            return DeviceType.SERIAL
        elif device_name in DeviceFactory.CALCULATION_DEVICES:
            return DeviceType.CALCULATION
        else:
            return DeviceType.OTHER

    @staticmethod
    def connect_serial_device(device_name: DeviceName) -> Optional[SerialWeatherDevice]:
        """
        Creates WeatherDevice object on the serial port specified by config files,
        and checks if the devices is connected properly
        :param device_name: type of device to create
        :return: a connected and functional WeatherDevice instance
        or None
        """

        # wrong device
        if device_name not in DeviceFactory.SERIAL_DEVICES:
            return None

        config_name = device_name.value

        with open(DeviceFactory.SERIAL_CONFIG_PATH, "r") as f:
            doc = tomlkit.load(f)
            default_port = doc[config_name]["com_port"]
            baud_rate = doc[config_name]["baud_rate"]

        if device_name == DeviceName.DAVIS_VANTAGE:
            device = VantagePro2()
        elif device_name == DeviceName.ARDUINO_IN:
            device = InsideArduino()
        elif device_name == DeviceName.ARDUINO_OUT:
            device = OutsideArduino()
        else:
            return None

        # there is a default port
        if device_name != "":
            # default port available
            if DeviceFactory._free_serial_ports.get(default_port, False):
                ser = serial.Serial(default_port, baud_rate)
                device.set_port(ser)

                # device connected
                if device.check_right_port():
                    return device

        # look for other port
        for other_port in DeviceFactory._free_serial_ports:
            # port is available
            if other_port != default_port and DeviceFactory._free_serial_ports[other_port]:
                ser = serial.Serial(default_port, baud_rate)
                device.set_port(ser)

                # device connected
                if device.check_right_port():
                    return device

        # can't connect device
        return None

    @staticmethod
    def create_calculation_device(device_name: DeviceName):
        """
        Creates a device that calculates values, using values from config files
        :param device_name: type of device to create
        :return: WeatherDevice object
        """
        # wrong device
        if device_name not in DeviceFactory.CALCULATION_DEVICES:
            return None

        # a device that calculates the sun's elevations
        if device_name == DeviceName.SUN_ELEVATION_CALCULATOR:
            config_name = device_name.value

            with open(DeviceFactory.CALCULATION_CONFIG_PATH, "r") as fp:
                doc = tomlkit.load(fp)
                table = doc[config_name]
                parameters = table["param"]

                # specific data for this device
                longitude = parameters["longitude"]
                latitude = parameters["latitude"]
                height = parameters["height"]

                return SunElevationDevice(longitude=longitude,
                                          latitude=latitude,
                                          height=height)
        else:
            return None

    @staticmethod
    def get_active_devices():
        """
        Checks which devices marked in the configurations as active
        :return: list of devices that are supposed to be active
        """
        devices = list()

        # with open(DeviceFactory.ACTIVE_DEVICES_CONFIG_PATH, "r") as fp:
        #     doc = tomlkit.load(fp)
        #
        #     for device_str in DeviceName:
        #         # device is active
        #         if doc[device_str]["active"]:
        #             device = DeviceName(device_str)
        #             devices.append(device)

        stations = cfg.datums['station_settings'].keys()
        for station in stations:
            enabled = cfg.datums['station_settings'][station]['enabled']
            if enabled:
                devices.append(station)

        return devices
