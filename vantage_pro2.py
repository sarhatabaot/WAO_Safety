import datetime
import logging
import time
from typing import List

import serial

from station import SerialStation
from utils import VantageProDatum, VantageProReading
from config.config import make_cfg
from db_access import make_db_manager, DbManager
from init_log import init_log
from sqlalchemy.orm import scoped_session

logger = logging.getLogger('davis')
init_log(logger)


class UnitConverter:
    @staticmethod
    def fahrenheit_to_celsius(degrees_f):
        return (degrees_f - 32.0) * (5.0 / 9.0)

    @staticmethod
    def mph_to_kph(speed_mph):
        return speed_mph / 1.60934


class LoopPacket:
    PacketLength = 99
    PacketDataLength = PacketLength - 2

    @classmethod
    def parse(cls, packet: bytes, timestamp: datetime.datetime) -> VantageProReading:
        if len(packet) != LoopPacket.PacketLength:
            raise f"expected {LoopPacket.PacketLength}, got {len(packet)} instead!"

        if not LoopPacket.is_crc_correct(packet):
            raise f"Bad CRC!"

        ret: VantageProReading = VantageProReading()

        pressure_bytes = packet[7:9]
        # pressure_out = LoopPacket._parse_barometer(pressure_bytes)
        ret.datums[VantageProDatum.Barometer] = LoopPacket._parse_barometer(pressure_bytes)

        # temperature_in = LoopPacket._parse_temperature(packet[9:11])
        ret.datums[VantageProDatum.InsideTemperature] = LoopPacket._parse_temperature(packet[9:11])

        # humidity_in = packet[11]
        ret.datums[VantageProDatum.InsideHumidity] = packet[11]

        # temperature_out = LoopPacket._parse_temperature(packet[12:14])
        ret.datums[VantageProDatum.OutsideTemperature] = LoopPacket._parse_temperature(packet[12:14])

        wind_speed_mph = packet[14]
        # wind_speed = UnitConverter.mph_to_kph(wind_speed_mph)
        ret.datums[VantageProDatum.WindSpeed] = UnitConverter.mph_to_kph(wind_speed_mph)

        # wind_direction = int.from_bytes(packet[16:18], "little")
        ret.datums[VantageProDatum.WindDirection] = int.from_bytes(packet[16:18], "little")

        # humidity_out = packet[33]
        ret.datums[VantageProDatum.OutSideHumidity] = packet[33]

        # solar_radiation = int.from_bytes(packet[44: 46], "little")
        ret.datums[VantageProDatum.SolarRadiation] = int.from_bytes(packet[44: 46], "little")

        # Convert inch/100 to inch to mm
        # rain_rate = int.from_bytes(packet[41: 42], "little") / 100.0 * 25.4
        ret.datums[VantageProDatum.RainRate] = int.from_bytes(packet[41: 42], "little") / 100.0 * 25.4

        ret.datums[VantageProDatum.UV] = packet[43]

        ret.tstamp = timestamp
        return ret

    @staticmethod
    def _parse_temperature(temp_bytes: bytes):
        return UnitConverter.fahrenheit_to_celsius(int.from_bytes(temp_bytes, "little") / 10)

    @staticmethod
    def _parse_barometer(bar_bytes: bytes):
        barometer = int.from_bytes(bar_bytes, "little")
        # inHg to mBar
        return barometer * 0.0338639 / 1000

    @staticmethod
    def is_crc_correct(packet: bytes):
        crc = 0

        for i in range(len(packet)):
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


class VantagePro2(SerialStation):

    db_manager: DbManager

    def __init__(self, name: str):
        self.name = name
        super().__init__(name=name)

        cfg = make_cfg()
        self.cfg = cfg.toml['stations']['davis']
        self.interval = cfg.station_settings[self.name].interval
        self.db_manager = make_db_manager()

    def detect(self, serial_ports: List[str]) -> List[str]:
        ret = serial_ports
        for serial_port in serial_ports:
            with serial.Serial(port=serial_port, baudrate=self.cfg['baud'], timeout=2) as ser:
                #
                # The VantagePro replies with 'TEST\n' when sent 'TEST\n'
                #
                try:
                    ser.write(b'\n')    # wake it up
                    buf = ser.read(2)
                    if buf != b'\n\r':
                        continue
                    ser.reset_input_buffer()
                    n = ser.write(b'TEST\n')
                    if n != 5:
                        continue
                    buf = ser.readline()
                    buf = ser.readline()
                    if buf == b'\rTEST\n':
                        ser.close()
                        ret.remove(serial_port)
                        self.port = serial_port
                        logger.info(f"Detected a VantagePro2 station on '{serial_port}' at {self.cfg['baud']} baud")
                        return ret
                except Exception as e:
                    ser.close()
        return ret

    @classmethod
    def datums(cls) -> List[str]:
        """
        The list of datums retrieved from a VantagePro2 station.

        The names are as per the VantagePro Serial Protocol, lower-cased and with underscores instead of spaces.

        :return:
            list of datum names
        """
        return [item.value for item in VantageProDatum]

    def fetcher(self):
        # print(f"{self.name}: fetcher is bypassed")
        # return
        try:
            self.ser = serial.Serial(port=self.port, baudrate=self.baud, timeout=self.timeout,
                                     write_timeout=self.write_timeout)
        except Exception as ex:
            logger.error(f"Could not open '{self.port}'", exc_info=ex)
            self.ser.close()
            return

        try:
            self.__wakeup()
        except Exception as ex:
            logger.error("failed to wake up the station", exc_info=ex)
            self.ser.close()
            return

        try:
            reading = self.__loop()
            logger.debug("got LOOP packet")
        except Exception as ex:
            logger.error("failed to get a LOOP packet", exc_info=ex)
            self.ser.close()
            return

        if reading:
            with self.lock:
                self.readings.push(reading)
            if hasattr(self, 'saver'):
                self.saver(reading)

    def saver(self, reading: VantageProReading) -> None:
        from db_access import DavisDbClass

        davis = DavisDbClass(
            temp_in=reading.datums[VantageProDatum.InsideTemperature],
            humidity_in=reading.datums[VantageProDatum.InsideHumidity],
            pressure_out=reading.datums[VantageProDatum.Barometer],
            temp_out=reading.datums[VantageProDatum.OutsideTemperature],
            humidity_out=reading.datums[VantageProDatum.OutSideHumidity],
            wind_speed=reading.datums[VantageProDatum.WindSpeed],
            wind_direction=reading.datums[VantageProDatum.WindDirection],
            rain=reading.datums[VantageProDatum.RainRate],
            solar_radiation=reading.datums[VantageProDatum.SolarRadiation],
            tstamp=reading.tstamp,
        )

        # db_manager.session.add(davis)
        # db_manager.session.commit()
        Session = scoped_session(self.db_manager.session_factory)
        session = Session()
        try:
            session.add(davis)
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            Session.remove()

    def check_right_port(self) -> bool:
        # wakeup if sleeping
        if not self.__wakeup():
            return False

        # check test
        if not self.__test():
            return False

        # check additional information
        # echo is not enough
        if not self._probe():
            return False

        # definitely a VantagePro
        return True

    def __wakeup(self) -> bool:
        expected_response = bytes([10, 13])
        wakeup_attempts = 3

        for _ in range(wakeup_attempts):
            try:
                self.ser.write(b"\n")
            except Exception as ex:
                logger.error(f"failed to wakeup station", exc_info=ex)
                raise

            response = self.ser.read(len(expected_response))
            # response = self.ser.read(1024)
            if len(response) == 0:
                raise Exception(f"Could not read {len(expected_response)} bytes in {self.ser.timeout} seconds")
            return response == expected_response

        return False

    def __test(self):
        # self.ser.reset_output_buffer()

        expected_response = b"TEST\n\r"
        self.ser.write(b"TEST\n")

        self.ser.read(2)
        response = self.ser.read(len(expected_response))

        return response == expected_response

    def _probe(self) -> bool:
        expected_response = bytes([6, 16])
        try:
            self.ser.write(b"WRD" + bytes([0x12, 0x4D]) + b"\n")
            response = self.ser.read(len(expected_response))
        except Exception as ex:
            logger.error(f"failed probing with WRD", exc_info=ex)
            return False

        return response == expected_response

    def __loop(self):
        try:
            self.ser.write(b"LOOP 1\n")
        except Exception as ex:
            logger.error(f"failed to send/receive a LOOP packet", exc_info=ex)
            return

        ack = self.ser.read(1)
        if len(ack) != 1:
            raise Exception(f"No ACK after sending 'LOOP 1'")

        loop_bytes = self.ser.read(99)
        if len(loop_bytes) != 99:
            raise Exception(f"Could not read 99 LOOP bytes (got only {len(loop_bytes)})")

        return LoopPacket.parse(loop_bytes, datetime.datetime.utcnow())


# if __name__ == "__main__":
#     v = VantagePro2('davis')
#     v.start()
