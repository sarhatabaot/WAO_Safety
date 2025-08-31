from station import IPStation
import httpx
from bs4 import BeautifulSoup
from enum import Enum
from typing import List
import logging
import subprocess
import datetime
import time

from init_log import init_log
from utils import TessWReading
from sqlalchemy.orm import scoped_session
from config.config import Config
from db_access import DbManager

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

    def __init__(self, name: str):
        self.wifi_interface = "wlo2"
        self.wifi_ssid = "TESS-stars1258"

        super().__init__(name)
        cfg = Config()
        self.cfg = cfg.toml['stations']['tessw']
        self.interval = cfg.station_settings[self.name].interval
        self.db_manager = DbManager()

    def run_shell_cmd(self, cmd: str) -> tuple:
        """
        Runs @cmd in a subprocess and returns a (status, stdout, stderr) tupple
        """
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode, result.stdout, result.stderr
        except subprocess.CalledProcessError as ex:
            logger.error(f"error running '{cmd}', {ex}")
            return None, None, None
    
    def check_wifi_interface_status(self) -> bool:
        """
        Tries to bring up the TESS-stars1258 WiFi SSID
        """
        _, stdout, _ = self.run_shell_cmd(cmd=f"ip link show {self.wifi_interface}")

        interface_is_up = False
        if 'state UP' in stdout:
            interface_is_up = True
        
        if not interface_is_up:
            self.run_shell_cmd(f"ifconfig {self.wifi_interface} up")
            time.sleep(3)
            _, stdout, _ = self.run_shell_cmd(f"ip link show {self.wifi_interface}")
            if 'state UP' in stdout:
                interface_is_up = True
            else:
                # logger.error(f"could not bring interface '{self.wifi_interface} up")
                return False
        
        if not interface_is_up:
            return False
        
        _, stdout, _ = self.run_shell_cmd("nmcli -t -f active,ssid dev wifi")
        if f"yes:{self.wifi_ssid}" in stdout:
            return True
        retcode, stdout, stderr = self.run_shell_cmd(f"nmcli dev wifi connect {self.wifi_ssid}")
        return retcode == 0

    def datums(self) -> List[str]:
        return [item.value for item in TessWDatum]

    def fetcher(self):
        if not self.check_wifi_interface_status():
            logger.error(f"tessw:fetcher: could not restore connection to '{self.wifi_ssid}' on '{self.wifi_interface}'")
            return

        url = f"http://{self.host}:{self.port}"
        try:
            response = httpx.request(method="GET", url=url, proxies={}, trust_env=False, timeout=10)
            response.raise_for_status()
        except Exception as ex:
            logger.debug(f"tessw:fetcher: exception {ex} (url={url})")
            return

        html = response.content.decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")
        for meta in soup.find_all("meta", attrs={"http-equiv": True}):
            meta.decompose()          # delete it from the tree

        import re

        h4_text = soup.h4.get_text(separator=" ", strip=True)   # flatten <br> to spaces, strip ends
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

        reading = TessWReading()
        reading.datums[TessWDatum.Cover] = self.cover
        reading.tstamp = datetime.datetime.utcnow()

        if reading:
            with self.lock:
                self.readings.push(reading)
            if hasattr(self, 'saver'):
                self.saver(reading)

    def latest_readings(self, datum: str, n: int = 1) -> list:
        return [self.cover] if datum == TessWDatum.Cover else []

    def saver(self, reading: TessWReading) -> None:
        from db_access import TessWDbClass

        logger.info(f"tessw:saver: saving cover={reading.datums[TessWDatum.Cover]}")

        _tessw = TessWDbClass(
            cover=reading.datums[TessWDatum.Cover],
            tstamp=reading.tstamp,
        )

        Session = scoped_session(self.db_manager.session_factory)
        session = Session()
        try:
            session.add(_tessw)
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            Session.remove()

    def calculate_sensors(self):
        pass


if __name__ == "__main__":
    tessw = TessW('tessw')
    tessw.fetcher()
    print(f"{tessw.cover=}")
