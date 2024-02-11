from station import IPStation, Reading
import httpx
import xmltodict
from enum import Enum
from typing import List
import socket

import logging
from init_log import init_log

logger = logging.getLogger('cyclope')
init_log(logger)


class CyclopeDatum(str, Enum):
    ZenithSeeing = "seeing_zenith"
    R0 = "R0"


class Cyclope(IPStation):

    zenith_seeing: float
    r0: float

    def __init(self, name: str):
        super().__init__(name)

    def datums(self) -> List[str]:
        return list(CyclopeDatum.__members__.keys())

    def fetcher(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((self.host, self.port))

                response = sock.recv(1024).decode()
                if int(response) != 200:
                    logger.error(f"Expected response 200, got '{response}'")
                    return

                sock.sendall(f"SysRequest <GetData>".encode())
                response = sock.recv(1024).decode()
                logger.debug(f"sent 'SysRequest <GetData>', got '{response}'")
                if not response.startswith("201\n"):
                    logger.error(f"sent 'SysRequest <GetData>', expected response 201, got '{response[0:2]}'")
                    return
                response = response[4:]
                #                   Returns a list string  ->
                #
                #                   <IS_Valid=True>
                #                   <UTC_DateMeasurement=%1.7f>
                #                   <UTC_DateMeasurement_Readable=%s>
                #                   <LCL_DateMeasurement=%1.7f>
                #                   <LCL_DateMeasurement_Readable=%s>
                #                   <Last_ZenithArcsec=%1.2f>
                #                   <Last_R0Arcsed=%1.2f>
                #
                #                   or
                #
                #                   <IS_Valid=False>

                sock.sendall("SysRequest <SysStatus>".encode())
                response = sock.recv(1024).decode()
                logger.debug(f"sent 'SysRequest <SysStatus>', got '{response}'")
                if not response.startswith("201\n"):
                    logger.error(f"sent 'SysRequest <SysStatus>', expected response 201, got '{response[0:2]}'")
                    return
                #           (*
                #            <State=Unknown|0>'
                #            <State=Idle|1>'
                #            <State=Idle (Day Time)|2>'
                #            <State=Seeking for star|3>'
                #            <State=Measuring|4>'
                #            <State=Star Lost|5>'
                #           *)

        except Exception as ex:
            logger.error(f"['{self.host}':{self.port}], Exception: {ex}")
        # reading = response
        # self.zenith_seeing = float(reading['Last_ZenithArcsec'])
        # self.r0 = float(reading['Last_R0Arcsec'])

    def latest_readings(self, datum: str, n: int = 1) -> list:

        if datum == CyclopeDatum.ZenithSeeing:
            return [self.zenith_seeing]
        elif datum == CyclopeDatum.R0:
            return [self.r0]

    def saver(self, reading: Reading) -> None:
        pass

    def calculate_sensors(self):
        pass