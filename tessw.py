from station import IPStation, Reading
import httpx
import xmltodict
from enum import Enum
from typing import List


class TessWDatum(str, Enum):
    Cover = "cover"


class TessW(IPStation):

    cover: float

    def __init(self, name: str):
        super().__init__(name)

    def datums(self) -> List[str]:
        return list(TessWDatum.__members__.keys())

    def fetcher(self):
        response = None
        url = f"http://{self.host}:{self.port}"

        try:
            response = httpx.request(method="GET", url=url)
            response.raise_for_status()
        except Exception as ex:
            self.logger.debug(f"Exception {ex} (url={url})")
            return

        reading = xmltodict(response.content)

        if not reading['IS_Valid']:
            self.logger.debug(f"Got IS_Valid=False")
            return

        self.cover = float(reading['XXX'])  # TBD

    def latest_readings(self, datum: str, n: int = 1) -> list:

        if datum == TessWDatum.Cover:
            return [self.cover]

    def saver(self, reading: Reading) -> None:
        pass

    def calculate_sensors(self):
        pass