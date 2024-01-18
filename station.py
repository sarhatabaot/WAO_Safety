import datetime
import threading

from utils import FixedSizeFifo, cfg
from abc import ABC, abstractmethod
from typing import List, Dict

import serial
import logging
import time

from config.config import split_source
from sensor import SensorSettings


class Reading:
    datums: dict
    tstamp: datetime.datetime

    def __init__(self):
        self.datums = dict()


class Sensor:
    name: str
    project: str
    datum: str
    is_safe: bool
    was_safe: bool
    is_settling: bool
    became_safe: datetime.datetime
    reasons: List[str]
    settings: SensorSettings
    settling_delta: datetime.timedelta

    def __init__(self, name: str, project: str, datum: str, settings: SensorSettings):
        self.name = name
        self.project = project
        self.datum = datum
        self.is_safe = False
        self.was_safe = False
        self.is_settling = False
        self.settings = settings
        self.reasons = []
        self.settling_delta = datetime.timedelta(seconds=settings.settling)


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
    sensors: list
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
        if name not in cfg.stations:
            raise f"bad station name '{name}' (not one of {cfg.stations}, in '{cfg.filename}')"

        if name not in cfg.enabled_stations:
            print(f"station {self.name} is not enabled in '{cfg.filename}'")
            return

        self.name = name
        self.logger = logging.getLogger(f"station-{self.name}")
        self.interval = cfg.get(f"stations.{self.name}.interval")
        self.sensors = list()

        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread = threading.Thread(name="loop-thread",
                                       target=self.fetcher_loop)

    def start(self):
        """
        At start() time a **Station** populates its sensors and starts the fetcher loop
        """

        # process the project-specific sensors
        for project in cfg.get('global.projects'):
            if project not in cfg.data or 'sensors' not in cfg.data[project]:
                continue
            sensors = cfg.data[project]['sensors'].keys()
            for sensor in sensors:
                defaults = {}
                project_settings = cfg.get(f"{project}.{sensor}")
                if sensor in cfg.data['sensors']:
                    defaults = cfg.get(f"sensors.{sensor}")

                d: Dict = dict()
                if defaults is not None:
                    d = defaults
                if project_settings is not None:
                    if d is not None:
                        d.update(project_settings)
                    else:
                        d = project_settings

                if 'enabled' not in d or not d['enabled']:
                    continue
                station, datum = split_source(d['source'])
                if station != self.name or datum not in self.datums():
                    continue

                self.sensors.append(Sensor(
                    name=sensor,
                    project=project,
                    datum=datum,
                    settings=SensorSettings(d),
                ))

        # process the project-agnostic sensors
        sensors = list(cfg.data['sensors'].keys())
        for sensor in sensors:
            d = cfg.get(f"sensors.{sensor}")

            if 'enabled' not in d or not d['enabled']:
                continue

            station, datum = split_source(d['source'])
            if station != self.name or datum not in self.datums():
                continue

            self.sensors.append(Sensor(
                name=sensor,
                project='default',
                datum=datum,
                settings=SensorSettings(d),
            ))

        nreadings = 1
        for sensor in self.sensors:
            nreadings = max(nreadings, sensor.settings.nreadings)
        self.logger.info(f"Allocating a {nreadings} deep fifo")
        self.readings = FixedSizeFifo(nreadings)

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
            self.calculate_sensors()
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
        max_size = self.readings.max_size
        curr_size = len(self.readings.data)
        if n > curr_size:
            raise Exception(f"station '{self.name}': not enough readings: wanted={n}, " +
                            f"got only {curr_size} out of max={max_size}")

        current = list()
        with self.lock:
            for reading in self.readings.data:
                current.append(reading.datums[datum])

        return current[curr_size-1-n:curr_size-1]

    def all_readings(self) -> FixedSizeFifo:
        return self.readings

    def calculate_sensors(self):
        sensor: Sensor
        for sensor in self.sensors:
            sensor.reasons = list()
            settings: SensorSettings = sensor.settings
            try:
                # try to get the readings needed by the sensor
                values = self.latest(settings.datum, settings.nreadings)
            except Exception as ex:
                sensor.is_safe = False
                sensor.reasons.append(f"{ex}")
                continue

            # check that the readings are in range
            baddies = 0
            for value in values:
                if value >= settings.min or value > settings.max:
                    baddies = baddies + 1

            is_safe = False
            if baddies > 0:
                is_safe = False
                sensor.reasons.append(
                    f"{baddies} out of {settings.nreadings} are out of " +
                    f"range (min={settings.min}, max={settings.max}")
            else:
                is_safe = True
                if not sensor.was_safe:
                    # the sensor just became safe
                    if settings.settling is not None:
                        # it has a settling period, start it now
                        sensor.became_safe = datetime.datetime.now()
                        is_safe = False
                        sensor.reasons.append(
                            f"started settling for {settings.settling} seconds")
                elif sensor.became_safe:
                    # a settling period was started
                    delta = datetime.datetime.now() - sensor.became_safe
                    if delta > sensor.settling_delta:
                        # the settling period ended
                        is_safe = True
                        sensor.became_safe = None

            sensor.is_safe = is_safe


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

        self.logger = logging.getLogger(f'SerialStation-{self.name}')
        config = cfg.get(f"stations.{name}")
        if config is None:
            msg = f"Cannot get configuration for station='{name}' from '{cfg.filename}'"
            self.logger.error(msg)
            raise Exception(msg)

        if name not in cfg.enabled_stations:
            msg = f"Station '{name}' not enabled in '{cfg.filename}'"
            self.logger.error(msg)
            raise Exception(msg)

        if 'interface' not in config:
            msg = f"Missing 'interface' in configuration for station='{name}' in '{cfg.filename}'"
            self.logger.error(msg)
            raise Exception(msg)
        if 'baud' not in config:
            msg = f"Missing 'baud' in configuration for station='{name}' in '{cfg.filename}'"
            self.logger.error(msg)
            raise Exception(msg)

        self.port = config['interface']
        self.baud = config['baud']
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

        self.logger = logging.getLogger(f'HTTPStation-{self.name}')
        config = cfg.get(f"stations.{name}")
        if config is None:
            msg = f"Cannot get configuration for station='{name}' from '{cfg.filename}'"
            self.logger.error(msg)
            raise Exception(msg)

        if name not in cfg.enabled_stations:
            msg = f"Station '{name}' not enabled in '{cfg.filename}'"
            self.logger.error(msg)
            raise Exception(msg)

        if 'host' not in config:
            msg = f"Missing 'host' in configuration for station='{name}' in '{cfg.filename}'"
            self.logger.error(msg)
            raise Exception(msg)
        if 'port' not in config:
            msg = f"Missing 'port' in configuration for station='{name}' in '{cfg.filename}'"
            self.logger.error(msg)
            raise Exception(msg)
        self.host = config['port']
        self.port = config['port']
        self.address = f"host={self.host}, port={self.port}"

    def fetcher(self) -> None:
        pass

    def saver(self, reading: Reading) -> None:
        pass
