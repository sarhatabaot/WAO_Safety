import datetime
import threading

from utils import FixedSizeFifo, cfg
from abc import ABC, abstractmethod
from typing import List

import serial
import logging
import time


class Reading:
    datums: dict
    tstamp: datetime.datetime


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
        A method that fetches the information from the **Station** and saves it in the `_readings` fifo
        """
        pass

    @abstractmethod
    def saver(self, reading: Reading) -> None:
        """
        A method that saves a reading from the **Station** to the database
        :return:
        """
        pass

    def __init__(self, name: str):
        """
        **Station** constructor

        :param name:
            name of the **Station**
        """
        if name not in cfg.stations:
            raise f"bad station name '{name}' (not one of {cfg.stations}, in '{cfg.filename}')"

        if name not in cfg.enabled_stations:
            print(f"station {self.name} is not enabled in '{cfg.filename}'")
            return

        self.name = name
        #
        # For each of the 'Projects' that have 'Sensors' using this station as their 'source'
        #  get the number of required readings, and allocate a fifo deep enough to store the largest required number.
        #
        projects = cfg.get('global.projects')
        sensors = cfg.datums['sensors'].keys()
        requirements = dict()
        this_station = self.name
        self.interval = cfg.get(f"stations.{self.name}.interval")

        for project in projects:
            for sensor in sensors:
                source = cfg.get(f"sensors.{sensor}.source")
                project_source: str = cfg.get(f"{project}.sensors.{sensor}.source")
                if project_source is not None:
                    source = project_source
                if source is not None and source.startswith(f"{this_station}:"):
                    # figure out how many readings are required for each referenced datum
                    datum = source.replace(f"{this_station}:", "")
                    if datum not in requirements:
                        requirements[datum] = list()
                    project_nreadings = cfg.get(f"{project}.sensors.{sensor}.nreadings")
                    if project_nreadings is None:
                        project_nreadings = 1
                    default_nreadings = cfg.get(f"sensors.{sensor}.nreadings")
                    if default_nreadings is None:
                        default_nreadings = 1
                    requirements[datum].append(max(project_nreadings, default_nreadings))

        self._readings = dict()
        for datum in requirements.keys():
            nreadings = max(requirements[datum])
            print(f"station '{self.name}': allocating {nreadings} deep fifo for _readings['{datum}']")
            self._readings[datum] = FixedSizeFifo(nreadings)

        if hasattr(self, 'fetcher'):
            self.lock = threading.Lock()
            self.stop_event = threading.Event()
            self.stop_event.clear()
            self.thread = threading.Thread(target=self.fetcher_loop)
            self.thread.start()

    def __del__(self):
        self.stop_event.set()

    def fetcher_loop(self):
        while not self.stop_event.is_set():
            start_time = time.time()
            self.fetcher()
            end_time = time.time()
            # sleep until end of interval
            remaining_time = self.interval - (end_time - start_time)
            time.sleep(remaining_time)

    def latest(self, datum: str, n: int = 1):
        if datum not in self._readings:
            keys = ", ".join(self._readings.keys())
            raise f"Bad datum '{datum}', must be one of {keys}"
        max_size = self._readings[datum].max_size
        curr_size = len(self._readings[datum].data)
        if n > curr_size:
            raise (f"station '{self.name}': not enough readings: wanted={n}, " +
                   f"got only {curr_size} out of max={max_size}")

        with self.lock:
            return self._readings[datum].data[curr_size-1-n:curr_size-1]

    def all_readings(self) -> dict:
        response = dict()
        for datum in self._readings.keys():
            response[datum] = self.latest(datum)
        return response


class SerialStation(Station):

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
            raise msg

        if name not in cfg.enabled_stations:
            msg = f"Station '{name}' not enabled in '{cfg.filename}'"
            self.logger.error(msg)
            raise msg

        if 'interface' not in config:
            msg = f"Missing 'interface' in configuration for station='{name}' in '{cfg.filename}'"
            self.logger.error(msg)
            raise msg
        if 'baud' not in config:
            msg = f"Missing 'baud' in configuration for station='{name}' in '{cfg.filename}'"
            self.logger.error(msg)
            raise msg

        self.port = config['interface']
        self.baud = config['baud']
        self.address = f"port={self.port}, baud={self.baud}"
        try:
            self.ser = serial.Serial(self.port, self.baud)
        except Exception as ex:
            self.logger.error(f"Cannot open serial at {self.address}", exc_info=ex)
            raise


class HTTPStation(Station):

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
            raise msg

        if name not in cfg.enabled_stations:
            msg = f"Station '{name}' not enabled in '{cfg.filename}'"
            self.logger.error(msg)
            raise msg

        if 'host' not in config:
            msg = f"Missing 'host' in configuration for station='{name}' in '{cfg.filename}'"
            self.logger.error(msg)
            raise msg
        if 'port' not in config:
            msg = f"Missing 'port' in configuration for station='{name}' in '{cfg.filename}'"
            self.logger.error(msg)
            raise msg
        self.host = config['port']
        self.port = config['port']
        self.address = f"host={self.host}, port={self.port}"
