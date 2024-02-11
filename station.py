from __future__ import annotations

import datetime
import logging
import threading
import time
from abc import ABC, abstractmethod
from datetime import timedelta as td
from typing import List
from copy import copy

import serial

from sensor import Sensor, MinMaxSettings
from utils import FixedSizeFifo, Never, formatted_float_list, SafetyResponse
from config.config import make_cfg
from init_log import init_log

cfg = make_cfg()

logger = logging.getLogger('station')
init_log(logger)


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
    *Readings* fifo (the depth of which being the maximal number of values required by the *Sensors*)

    *Sensors* get a reference to the **Station**'s *Readings* fifo and use the latest ones they need to make safety
    decisions.
    """
    name: str
    interval: int
    readings: FixedSizeFifo
    nreadings: int
    sensors: List[Sensor]
    logger: logging.Logger
    settings: None

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

        if name not in cfg.enabled_stations:
            print(f"station {self.name} is not enabled in '{cfg.filename}'")
            return

        self.name = name
        
        self.interval = cfg.station_settings[name].interval
        self.sensors = list()

        nreadings = 1
        for project in cfg.projects:
            # foreach project
            for sensor in cfg.sensors[project]:
                # foreach sensor
                if sensor.settings.station == self.name:
                    # if the data is sourced from this station
                    existing = [s.name for s in self.sensors if s.name == sensor.name]
                    if len(existing) == 0:
                        self.sensors.append(sensor)
                        nreadings = max(nreadings, sensor.settings.nreadings)

        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread = threading.Thread(name="loop-thread",
                                       target=self.fetcher_loop)

        logger.debug(f"allocating fifo ({nreadings} deep)")
        cfg.station_settings[self.name].nreadings = nreadings
        self.readings = FixedSizeFifo(nreadings)

    def start(self):
        if hasattr(self, 'fetcher'):
            self.thread.start()

    def __del__(self):
        self.stop_event.set()

    def fetcher_loop(self):
        """
        A forever loop, to be started in a Thread.

        * Fetches the **Station**'s values
        * Calculates the sensors' safety
        * Sleeps as per the **Station**'s interval setting
        """
        while not self.stop_event.is_set():
            start_time = time.time()
            try:
                self.fetcher()
                self.calculate_sensors()
            except Exception as ex:
                logger.error(f"Could not fetch and calculate sensors", exc_info=ex)

            end_time = time.time()
            # sleep until end of interval
            remaining_time = self.interval - (end_time - start_time)
            if remaining_time > 0:
                time.sleep(remaining_time)

    def latest_readings(self, datum: str, n: int = 1) -> list:
        """
        Get the latest values for a *datum*
        :param datum: The *datum* in question
        :param n: How many values
        :return: A list of values
        """

        current = list()
        with self.lock:
            for reading in self.readings.data:
                current.append(reading.datums[datum])

        latest = current[-n:]
        logger.debug(f"datum '{datum}': all values: {formatted_float_list(current)}, " +
                          f"latest values: {formatted_float_list(latest)}")

        return latest

    def all_readings(self) -> FixedSizeFifo:
        with self.lock:
            readings = copy(self.readings)
        return readings

    def calculate_sensors(self):
        """
        Called each time a new reading is acquired from the station
        """
        sensor: Sensor

        if self.sensors:
            logger.debug("starting calculations")

        for sensor in self.sensors:
            if not sensor.settings.enabled:
                continue

            sensor.reasons = list()
            values_were_safe = (sensor.values_out_of_range() == 0)

            msg = f"{sensor.settings.project:7s}: sensor '{sensor.name}'"

            new_values = copy(self.latest_readings(sensor.settings.datum, sensor.settings.nreadings))
            sensor.values = new_values
            if len(new_values) < sensor.settings.nreadings:
                sensor.safe = False
                reason = (f"only {len(new_values)} (out of {sensor.settings.nreadings}) " +
                          f"are available: {formatted_float_list(new_values)}")
                sensor.reasons.append(f"sensor '{sensor.name}': " + reason)
                logger.debug(msg + reason)
                continue

            if sensor.settings.nreadings == 1 and hasattr(self, 'is_safe') and callable(self.is_safe):
                # the station has its own is_safe method
                sensor.values = new_values[0]
                found = [s for s in cfg.sensors[sensor.settings.project] if s.name == sensor.name]
                if found:
                    found[0].values = sensor.values
                response: SafetyResponse = self.is_safe(sensor)
                sensor.safe = response.safe
                sensor.reasons = response.reasons
            else:
                # check that the new_values are in range
                if not isinstance(sensor.settings, MinMaxSettings):
                    # sanity check
                    raise Exception(f"{msg}: SHOULD have settings of type 'MinMaxSettings' " +
                                    f"(not '{type(sensor.settings)})")
                sensor.values = new_values
                found = [s for s in cfg.sensors[sensor.settings.project] if s.name == sensor.name]
                if found:
                    found[0].values = sensor.values
                baddies = sensor.values_out_of_range()
                values_are_safe = baddies == 0

                if values_are_safe:
                    if values_were_safe:
                        sensor.safe = True
                        sensor.reasons = None
                    else:
                        if 'settling' in sensor.settings and sensor.settings.settling is not None:
                            if sensor.started_settling is not Never:
                                if sensor.has_settled():
                                    # the settling period ended
                                    sensor.safe = True
                                    sensor.reasons = None
                                else:
                                    sensor.safe = False
                                    end = sensor.started_settling + td(seconds=sensor.settings.settling)
                                    td_left = end - datetime.datetime.now()
                                    sensor.reasons.append(f"sensor '{sensor.name}': " + f"settling for {td_left} more")
                            else:
                                # start the settling period
                                sensor.started_settling = datetime.datetime.now()
                                sensor.safe = False
                                sensor.reasons.append(
                                    f"sensor '{sensor.name}': " +
                                    f"started settling for {sensor.settings.settling} seconds")

                else:
                    sensor.safe = False
                    sensor.started_settling = Never
                    sensor.reasons.append(
                        f"sensor '{sensor.name}': " + f"{baddies} out of {sensor.settings.nreadings} are out of " +
                        f"range (min={sensor.settings.min}, max={sensor.settings.max}), " +
                        f"values={formatted_float_list(new_values)}")

            msg = f"{msg}: values: {formatted_float_list(new_values)}, is "
            if sensor.safe:
                msg += "safe"
            else:
                why = ", ".join(sensor.reasons)
                msg += f"not safe, reasons: {why}"
            logger.debug(msg)


class SerialStation(Station):
    """
    A weather station that gets its values from a serial port
    """
    port: str
    baud: int
    address: str
    ser: serial.Serial
    timeout: None
    write_timeout: None

    def __init__(self, name: str):
        super().__init__(name)

        settings = cfg.station_settings[name]
        if settings is None:
            msg = f"Cannot get configuration from '{cfg.filename}'"
            logger.error(msg)
            raise Exception(msg)

        if name not in cfg.enabled_stations:
            msg = f"not enabled in '{cfg.filename}'"
            logger.error(msg)
            raise Exception(msg)

        if settings.serial is None:
            msg = f"Missing 'serial' in configuration '{cfg.filename}'"
            logger.error(msg)
            raise Exception(msg)

        if settings.baud is None:
            msg = f"Missing 'baud' in configuration in '{cfg.filename}'"
            logger.error(msg)
            raise Exception(msg)

        self.timeout = settings.timeout if hasattr(settings, 'timeout') else None
        self.write_timeout = settings.write_timeout if hasattr(settings, 'write_timeout') else None

        self.port = settings.serial
        self.baud = settings.baud
        self.address = f"port={self.port}, baud={self.baud}"

        #
        # NOTE: The serial port will be open/closed by the fetcher method
        #

        # try:
        #     self.ser = serial.Serial(port=self.port, baudrate=self.baud, timeout=self.timeout)
        # except Exception as ex:
        #     logger.error(f"Cannot open serial at {self.address}", exc_info=ex)
        #     raise

    def fetcher(self) -> None:
        pass

    def saver(self, reading: Reading) -> None:
        pass


class IPStation(Station):
    """
    A weather Station that gets its values via HTTP
    """

    host: str
    port: int
    address: str

    def __init__(self, name: str):
        super().__init__(name=name)

        settings = cfg.toml['stations'][name]
        if settings is None:
            msg = f"Cannot get configuration from '{cfg.filename}'"
            logger.error(msg)
            raise Exception(msg)

        if name not in cfg.enabled_stations:
            msg = f"not enabled in '{cfg.filename}'"
            logger.error(msg)
            raise Exception(msg)

        if settings['host'] is None:
            msg = f"station '{name}', missing 'host' in configuration in '{cfg.filename}'"
            logger.error(msg)
            raise Exception(msg)

        if settings['port'] is None:
            msg = f"station '{name}', missing 'port' in configuration in '{cfg.filename}'"
            logger.error(msg)
            raise Exception(msg)

        self.host = settings['host']
        self.port = settings['port']
        self.address = f"host={self.host}, port={self.port}"

    def fetcher(self) -> None:
        pass

    def saver(self, reading: Reading) -> None:
        pass
