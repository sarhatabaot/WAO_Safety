from station import IPStation, Reading
import httpx
from bs4 import BeautifulSoup
from enum import Enum
from typing import List
import logging

from init_log import init_log

logger = logging.getLogger('tessw')
init_log(logger)


class TessWDatum(str, Enum):
    Cover = "cover"

#<!DOCTYPE html>
#    <html>
#        <head>
#            <meta name="viewport" content="width=device-width,user-scalable=0">
#            <title>AP mode</title>
#        </head>
#        <body>
#            <META HTTP-EQUIV="Refresh" Content= "4" /> <h2>STARS4ALL<br>TESS-W AP Mode</h2><h4><br><br> T. IR :   24.21 &ordm;C<br> T. Sens:   29.09 &ordm;C<br> Mag. :  16.23 mv/as2 f : 40.98 Hz<br></h4><p><a href="/config">Show Settings</a></p>
#        </body>
#    </html>

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
            response = httpx.request(method="GET", url=url, proxies={}, trust_env=False, timeout=10)
            response.raise_for_status()
        except Exception as ex:
            logger.debug(f"Exception {ex} (url={url})")
            return

        html = response.content.decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")
        for meta in soup.find_all("meta", attrs={"http-equiv": True}):
            meta.decompose()          # delete it from the tree

        from textwrap import dedent
        import re

        h4_text = soup.h4.get_text(" ", strip=True)   # flatten <br> to spaces, strip ends
        # "T. IR : 25.31 °C T. Sens: 30.41 °C Mag. : 15.75 mv/as2 f : 63.61 Hz"

        pattern = re.compile(
            r"T\. IR\s*:\s*(?P<tSky>[0-9.]+).*?"
            r"T\. Sens:\s*(?P<tAmb>[0-9.]+).*?"
            r"Mag\.\s*:\s*(?P<mag>[0-9.]+).*?"
            r"f\s*:\s*(?P<freq>[0-9.]+)",
            re.I | re.S,
        )
        m = pattern.search(h4_text)
        percent = 100 - (3 * (float(m["tAmb"]) - float(m["tSky"])))
        self.cover = max(percent, 0.0)

    def latest_readings(self, datum: str, n: int = 1) -> list:

        if datum == TessWDatum.Cover:
            return [self.cover]

    def saver(self, reading: Reading) -> None:
        pass

    def calculate_sensors(self):
        pass


if __name__ == "__main__":
    tessw = TessW('tessw')
    tessw.fetcher()
    print(f"{tessw.cover=}")
