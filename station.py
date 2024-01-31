from __future__ import annotations

import datetime
import logging
import threading
import time
from abc import ABC, abstractmethod
from datetime import timedelta as td
from typing import List

import serial

from init_log import init_log
from sensor import SensorSettings, Sensor
from utils import FixedSizeFifo
from utils import Never

from config.config import cfg


class SafetyResponse:
    """
    The response from a **Sensor** when asked if it is is_safe
    """
    safe: bool          # Is it is_safe?
    reasons: List[str]  # Why it is *unsafe*

    def __init__(self, safe: bool = True, reasons: List[str] = None):
        self.safe = safe
        self.reasons = reasons if reasons is not None else list()


class Reading:
    datums: dict
    tstamp: datetime.datetime

    def __init__(self):
        self.datums = dict()


class Station(ABC):
    """
    A **Station** periodically reads a *data-source* from which it gets a bunch of *datums*.

    * Some acquired *datums* get stored in the *database* along with a time-stamp.
    * Some *datums* may be required by *Sensors* (via their *source* attributes) for different *Projects*.
    If a specific *datum* is required by a 'Sensor', it becomes a *Reading* and is stored in the **Station**'s
    *Readings* fifo (the depth of which being the maximal number of readings required by the *Sensors*)

    *Sensors* get a reference to the **Station**'s *Readings* fifo and use the latest ones they need to make safety
    decisions.
    """
    name: str
    interval: int
    readings: FixedSizeFifo
    sensors: List[Sensor]
    logger: logging.Logger

    @classmethod
    def datums(cls) -> List[str]:
        """
        A list of datums supported by this **Station**
        :return: list of datum names
        """
        pass

    @abstractmethod
    def fetcher(self) -> None:
        """
        Fetches a reading from the **Station**
        """
        pass

    @abstractmethod
    def saver(self, reading: Reading) -> None:
        """
        Saves a **Station** reading (e.g. to the database)
        """
        pass

    def __init__(self, name: str):
        """
        **Station** constructor

        :param name: The **Station**'s name
        """

        from config.config import cfg

        if name not in cfg.enabled_stations:
            print(f"station {self.name} is not enabled in '{cfg.filename}'")
            return

        self.name = name
        self.logger = logging.getLogger(self.name)
        init_log(self.logger)
        self.interval = cfg.stations[name].interval
        self.sensors = list()

        nreadings = 1
        for project in cfg.projects:
            for sensor in cfg.sensors[project]:
                if sensor.settings.station == self.name:
                    existing = [s.name for s in self.sensors if s.name == sensor.name]
                    if len(existing) == 0:
                        self.sensors.append(sensor)
                        nreadings = max(nreadings, sensor.settings.nreadings)

        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread = threading.Thread(name="loop-thread",
                                       target=self.fetcher_loop)

        self.logger.info(f"allocating fifo ({nreadings} deep)")
        self.readings = FixedSizeFifo(nreadings)

    def start(self):
        if hasattr(self, 'fetcher'):
            self.thread.start()

    def __del__(self):
        self.stop_event.set()

    def fetcher_loop(self):
        """
        A forever loop, to be started in a Thread.

        * Fetches the **Station**'s readings
        * Calculates the sensors' safety
        * Sleeps as per the **Station**'s interval setting
        """
        while not self.stop_event.is_set():
            start_time = time.time()
            self.fetcher()
            self.calc()
            end_time = time.time()
            # sleep until end of interval
            remaining_time = self.interval - (end_time - start_time)
            time.sleep(remaining_time)

    def latest(self, datum: str, n: int = 1):
        """
        Get the latest values for a *datum*
        :param datum: The *datum* in question
        :param n: How many values
        :return: A list of values
        """
        curr_size = len(self.readings.data)
        if n > curr_size:
            raise Exception(f"not enough readings: {curr_size} of {n}")

        current = list()
        with self.lock:
            for reading in self.readings.data:
                current.append(reading.datums[datum])

        return current[curr_size-1-n:curr_size-1]

    def all_readings(self) -> FixedSizeFifo:
        return self.readings

    def calc(self):
        """
        Called each time a new reading is acquired from the station
        """
        sensor: Sensor

        for sensor in self.sensors:
            settings: SensorSettings = sensor.settings
            reasons = list()  # start a fresh one

            values = []
            is_safe = True
            try:
                # try to get the readings needed by the sensor
                values = self.latest(settings.datum, settings.nreadings)
            except Exception as ex:
                is_safe = False
                reasons.append(f"{ex}")

            if values is not None:
                if settings.nreadings == 1 and hasattr(self, 'is_safe') and callable(self.is_safe):
                    is_safe = self.is_safe(values[0], settings)
                else:
                    # check that the readings are in range
                    baddies = 0
                    for value in values:
                        if value < settings.min or value >= settings.max:
                            baddies = baddies + 1

                    is_safe = True
                    if baddies > 0:
                        is_safe = False
                        reasons.append(
                            f"{baddies} out of {settings.nreadings} are out of " +
                            f"range (min={settings.min}, max={settings.max})")
                    else:
                        if not sensor.previous_reading_was_safe:
                            # the sensor just became safe
                            if settings.settling is not None:
                                # it has a settling period, start it now
                                sensor.became_safe = datetime.datetime.now()
                                is_safe = False
                                reasons.append(
                                    f"started settling for {settings.settling} seconds")
                        elif sensor.became_safe is not Never:
                            # the settling period ended
                            is_safe = sensor.has_settled()
                            if not is_safe:
                                end = sensor.became_safe + td(seconds=sensor.settings.settling)
                                td_left = end - datetime.datetime.now()
                                reasons.append(f"Settling for {td_left} more")

            sensor.safe = is_safe
            sensor.reasons = reasons
            sensor.previous_reading_was_safe = is_safe

            if sensor.safe:
                msg = f"'{sensor.name}' is safe"
            else:
                why = ", ".join(sensor.reasons)
                msg = f"'{sensor.name}' is not safe, {why}"
            self.logger.debug(msg)


class SerialStation(Station):
    """
    A weather station that gets its readings from a serial port
    """
    port: str
    baud: int
    address: str
    ser: serial.Serial

    def __init__(self, name: str):
        super().__init__(name)

        settings = cfg.stations[name]
        if settings is None:
            msg = f"Cannot get configuration from '{cfg.filename}'"
            self.logger.error(msg)
            raise Exception(msg)

        if name not in cfg.enabled_stations:
            msg = f"not enabled in '{cfg.filename}'"
            self.logger.error(msg)
            raise Exception(msg)

        if settings.interface is None:
            msg = f"Missing 'interface' in configuration '{cfg.filename}'"
            self.logger.error(msg)
            raise Exception(msg)
        if settings.baud is None:
            msg = f"Missing 'baud' in configuration in '{cfg.filename}'"
            self.logger.error(msg)
            raise Exception(msg)

        self.port = settings.interface
        self.baud = settings.baud
        self.address = f"port={self.port}, baud={self.baud}"
        try:
            self.ser = serial.Serial(self.port, self.baud)
        except Exception as ex:
            self.logger.error(f"Cannot open serial at {self.address}", exc_info=ex)
            raise

    def fetcher(self) -> None:
        pass

    def saver(self, reading: Reading) -> None:
        pass


class HTTPStation(Station):
    """
    A weather Station that gets its readings via HTTP
    """

    host: str
    port: int
    address: str

    def __init__(self, name: str):
        super().__init__(name=name)

        settings = cfg.get(f"stations.{name}")
        if settings is None:
            msg = f"Cannot get configuration from '{cfg.filename}'"
            self.logger.error(msg)
            raise Exception(msg)

        if name not in cfg.enabled_stations:
            msg = f"not enabled in '{cfg.filename}'"
            self.logger.error(msg)
            raise Exception(msg)

        if settings.host is None:
            msg = f"Missing 'host' in configuration in '{cfg.filename}'"
            self.logger.error(msg)
            raise Exception(msg)
        if settings.port:
            msg = f"Missing 'port' in configuration in '{cfg.filename}'"
            self.logger.error(msg)
            raise Exception(msg)

        self.host = settings.port
        self.port = settings.port
        self.address = f"host={self.host}, port={self.port}"

    def fetcher(self) -> None:
        pass

    def saver(self, reading: Reading) -> None:
        pass
