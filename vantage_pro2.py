import datetime
from typing import Optional

from serial import Serial

from serial_weather_device import SerialWeatherDevice
from weather_measurement import WeatherMeasurement
from weather_parameter import WeatherParameter


class UnitConverter:
    @staticmethod
    def fahrenheit_to_celsius(degrees_f):
        return (degrees_f - 32.0) * (5.0 / 9.0)

    @staticmethod
    def mph_to_kph(speed_mph):
        return speed_mph / 1.60934


CONFIG_PATH = "/home/ocs/python/security/WeatherSafety/serial_config.toml"


class LoopPacket:
    PacketLength = 99
    PacketDataLength = 97

    def __init__(self, /, timestamp, pressure_out, temperature_in, temperature_out,
                 humidity_in, humidity_out, wind_speed, wind_direction, solar_radiation, rain_rate):
        self.timestamp: datetime.datetime = timestamp
        self.pressure_out: float = pressure_out
        self.temperature_in: float = temperature_in
        self.temperature_out: float = temperature_out
        self.humidity_in: int = humidity_in
        self.humidity_out: int = humidity_out
        self.wind_speed: float = wind_speed
        self.wind_direction: int = wind_direction
        self.solar_radiation = solar_radiation
        self.rain_rate = rain_rate

    @classmethod
    def parse(cls, packet: bytes, timestamp: datetime.datetime):
        if len(packet) != LoopPacket.PacketLength:
            return None

        if not LoopPacket.is_crc_correct(packet):
            return None

        pressure_bytes = packet[7:9]
        pressure_out = LoopPacket._parse_barometer(pressure_bytes)

        temperature_in = LoopPacket._parse_temperature(packet[9:11])

        humidity_in = packet[11]

        temperature_out = LoopPacket._parse_temperature(packet[12:14])

        wind_speed_mph = packet[14]
        wind_speed = UnitConverter.mph_to_kph(wind_speed_mph)

        wind_direction = int.from_bytes(packet[16:18], "little")
        humidity_out = packet[33]

        solar_radiation = int.from_bytes(packet[44: 46], "little")

        # Convert inch/100 to inch to mm
        rain_rate = int.from_bytes(packet[41: 42], "little") / 100.0 * 25.4

        return LoopPacket(timestamp=timestamp,
                          pressure_out=pressure_out,
                          temperature_in=temperature_in,
                          temperature_out=temperature_out,
                          humidity_in=humidity_in,
                          humidity_out=humidity_out,
                          wind_speed=wind_speed,
                          wind_direction=wind_direction,
                          solar_radiation=solar_radiation,
                          rain_rate=rain_rate)

    @staticmethod
    def _parse_temperature(temp_bytes: bytes):
        return UnitConverter.fahrenheit_to_celsius(int.from_bytes(temp_bytes, "little") / 10)

    @staticmethod
    def _parse_barometer(bar_bytes: bytes):
        barometer = int.from_bytes(bar_bytes, "little")
        # inHg / 1000 to mmHg to hPa to bar
        return (barometer * 1000.0 / 25.4) * 1.33322 / 1000.0

    @staticmethod
    def is_crc_correct(packet: bytes):
        crc = 0

        for i in range(len(packet)):
            # print("val = " + str((crc >> 8) ^ packet[i]))
            crc = LoopPacket._crc_table[(crc >> 8) ^ packet[i]] ^ ((crc << 8) % (2 ** 16))

        return crc == 0

    _crc_table = [0x0, 0x1021, 0x2042, 0x3063, 0x4084, 0x50a5, 0x60c6, 0x70e7,
                  0x8108, 0x9129, 0xa14a, 0xb16b, 0xc18c, 0xd1ad, 0xe1ce, 0xf1ef,
                  0x1231, 0x210, 0x3273, 0x2252, 0x52b5, 0x4294, 0x72f7, 0x62d6,
                  0x9339, 0x8318, 0xb37b, 0xa35a, 0xd3bd, 0xc39c, 0xf3ff, 0xe3de,
                  0x2462, 0x3443, 0x420, 0x1401, 0x64e6, 0x74c7, 0x44a4, 0x5485,
                  0xa56a, 0xb54b, 0x8528, 0x9509, 0xe5ee, 0xf5cf, 0xc5ac, 0xd58d,
                  0x3653, 0x2672, 0x1611, 0x630, 0x76d7, 0x66f6, 0x5695, 0x46b4,
                  0xb75b, 0xa77a, 0x9719, 0x8738, 0xf7df, 0xe7fe, 0xd79d, 0xc7bc,
                  0x48c4, 0x58e5, 0x6886, 0x78a7, 0x840, 0x1861, 0x2802, 0x3823,
                  0xc9cc, 0xd9ed, 0xe98e, 0xf9af, 0x8948, 0x9969, 0xa90a, 0xb92b,
                  0x5af5, 0x4ad4, 0x7ab7, 0x6a96, 0x1a71, 0xa50, 0x3a33, 0x2a12,
                  0xdbfd, 0xcbdc, 0xfbbf, 0xeb9e, 0x9b79, 0x8b58, 0xbb3b, 0xab1a,
                  0x6ca6, 0x7c87, 0x4ce4, 0x5cc5, 0x2c22, 0x3c03, 0xc60, 0x1c41,
                  0xedae, 0xfd8f, 0xcdec, 0xddcd, 0xad2a, 0xbd0b, 0x8d68, 0x9d49,
                  0x7e97, 0x6eb6, 0x5ed5, 0x4ef4, 0x3e13, 0x2e32, 0x1e51, 0xe70,
                  0xff9f, 0xefbe, 0xdfdd, 0xcffc, 0xbf1b, 0xaf3a, 0x9f59, 0x8f78,
                  0x9188, 0x81a9, 0xb1ca, 0xa1eb, 0xd10c, 0xc12d, 0xf14e, 0xe16f,
                  0x1080, 0xa1, 0x30c2, 0x20e3, 0x5004, 0x4025, 0x7046, 0x6067,
                  0x83b9, 0x9398, 0xa3fb, 0xb3da, 0xc33d, 0xd31c, 0xe37f, 0xf35e,
                  0x2b1, 0x1290, 0x22f3, 0x32d2, 0x4235, 0x5214, 0x6277, 0x7256,
                  0xb5ea, 0xa5cb, 0x95a8, 0x8589, 0xf56e, 0xe54f, 0xd52c, 0xc50d,
                  0x34e2, 0x24c3, 0x14a0, 0x481, 0x7466, 0x6447, 0x5424, 0x4405,
                  0xa7db, 0xb7fa, 0x8799, 0x97b8, 0xe75f, 0xf77e, 0xc71d, 0xd73c,
                  0x26d3, 0x36f2, 0x691, 0x16b0, 0x6657, 0x7676, 0x4615, 0x5634,
                  0xd94c, 0xc96d, 0xf90e, 0xe92f, 0x99c8, 0x89e9, 0xb98a, 0xa9ab,
                  0x5844, 0x4865, 0x7806, 0x6827, 0x18c0, 0x8e1, 0x3882, 0x28a3,
                  0xcb7d, 0xdb5c, 0xeb3f, 0xfb1e, 0x8bf9, 0x9bd8, 0xabbb, 0xbb9a,
                  0x4a75, 0x5a54, 0x6a37, 0x7a16, 0xaf1, 0x1ad0, 0x2ab3, 0x3a92,
                  0xfd2e, 0xed0f, 0xdd6c, 0xcd4d, 0xbdaa, 0xad8b, 0x9de8, 0x8dc9,
                  0x7c26, 0x6c07, 0x5c64, 0x4c45, 0x3ca2, 0x2c83, 0x1ce0, 0xcc1,
                  0xef1f, 0xff3e, 0xcf5d, 0xdf7c, 0xaf9b, 0xbfba, 0x8fd9, 0x9ff8,
                  0x6e17, 0x7e36, 0x4e55, 0x5e74, 0x2e93, 0x3eb2, 0xed1, 0x1ef0]

    def to_weather_measurement(self) -> WeatherMeasurement:
        data = {WeatherParameter.TEMPERATURE_IN: self.temperature_in,
                WeatherParameter.TEMPERATURE_OUT: self.temperature_out,
                WeatherParameter.HUMIDITY_IN: self.humidity_in,
                WeatherParameter.HUMIDITY_OUT: self.humidity_out,
                WeatherParameter.PRESSURE_OUT: self.pressure_out,
                WeatherParameter.WIND_SPEED: self.wind_speed,
                WeatherParameter.WIND_DIRECTION: self.wind_direction,
                WeatherParameter.SOLAR_RADIATION: self.solar_radiation,
                WeatherParameter.RAIN: self.rain_rate}

        return WeatherMeasurement(data, self.timestamp)


class VantagePro2(SerialWeatherDevice):
    def __init__(self, ser: Optional[Serial] = None):
        super().__init__(ser)

    def list_measurements(self):
        return {WeatherParameter.TEMPERATURE_IN,
                WeatherParameter.HUMIDITY_IN,
                WeatherParameter.PRESSURE_OUT,
                WeatherParameter.TEMPERATURE_OUT,
                WeatherParameter.HUMIDITY_OUT,
                WeatherParameter.WIND_SPEED,
                WeatherParameter.WIND_DIRECTION,
                WeatherParameter.RAIN,
                WeatherParameter.SOLAR_RADIATION}

    def measure_parameter(self, parameter: WeatherParameter):
        if not self.can_measure(parameter):
            return None

        if not self.__wakeup():
            return None

        measurement = self.__loop().to_weather_measurement()

        return measurement.get_parameter(parameter)

    def measure_all(self):
        if not self.__wakeup():
            return None

        measurement = self.__loop().to_weather_measurement()

        return measurement

    def check_right_port(self) -> bool:
        print("checking if vantage is connected")
        # wakeup if sleeping
        if not self.__wakeup():
            print("sleeping")
            return False

        # check test
        if not self.__test():
            print("failed test")
            return False

        # check additional information
        # echo is not enough
        if not self.__wrd():
            print("failed version")
            return False

        # definitely a VantagePro
        return True

    def __wakeup(self):
        expected_response = bytes([10, 13])
        wakeup_attempts = 3

        for _ in range(wakeup_attempts):
            self.ser.write(b"\n")
            response = self.ser.read(len(expected_response))
            print(f"wakeup {response}")

            if response == expected_response:
                print("woke up")
                return True

        return False

    def __test(self):
        # TODO: fix this
        # self.ser.reset_output_buffer()

        expected_response = b"TEST\n\r"
        self.ser.write(b"TEST\n")

        delim = self.ser.read(2)
        response = self.ser.read(len(expected_response))
        # print(response)
        print(f"test response: {response}")

        return response == expected_response

    def __wrd(self):
        expected_response = bytes([6, 16])
        self.ser.write(b"WRD" + bytes([0x12, 0x4D]) + b"\n")

        response = self.ser.read(len(expected_response))
        return response == expected_response

    def __loop(self):
        self.ser.write(b"LOOP 1\n")
        self.ser.read(1)

        loop_packet = self.ser.read(99)
        measurement = LoopPacket.parse(loop_packet, datetime.datetime.now())

        return measurement
