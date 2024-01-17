import datetime
import threading

from utils import FixedSizeFifo, cfg
from abc import ABC, abstractmethod
from typing import List, Dict

import serial
import logging
import time

from config.config import split_source
from sensor import Setting


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
    clients: Dict[str, Dict[str, Dict[str, Setting]]]

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
        requirements = dict()
        this_station = self.name
        self.interval = cfg.get(f"stations.{self.name}.interval")
        self.clients = dict()

        # for project in projects:
        #     if not hasattr(cfg.data, project):
        #         continue
        #     if not hasattr(cfg.data[project], 'sensors'):
        #         continue
        #
        #     for sensor in cfg.data[project]['sensors'].keys():
        #         source = cfg.get(f"sensors.{sensor}.source")
        #         project_source: str = cfg.get(f"{project}.sensors.{sensor}.source")
        #         if project_source is not None:
        #             source = project_source
        #         if source is None:
        #             continue
        #         station, datum = split_source(source)
        #         if station != this_station:
        #             continue
        #
        #         if datum not in requirements:
        #             requirements[datum] = 1
        #         project_nreadings = cfg.get(f"{project}.sensors.{sensor}.nreadings")
        #         if project_nreadings is None:
        #             project_nreadings = 1
        #         default_nreadings = cfg.get(f"sensors.{sensor}.nreadings")
        #         if default_nreadings is None:
        #             default_nreadings = 1
        #         requirements[datum] = max(project_nreadings, default_nreadings)
        #
        # nreadings = 1
        # for datum in requirements.keys():
        #     nreadings = max(nreadings, requirements[datum])
        #
        # print(f"station '{self.name}': allocating {nreadings} deep fifo")
        # self.readings = FixedSizeFifo(nreadings)

        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread = threading.Thread(name="loop-thread",
                                       target=self.fetcher_loop)

    def start(self):
        """
        At start() time a **Station** populates its clients and starts the fetcher loop
        """
        if self.name != 'calculator':
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
                    settings = {}
                    if project_settings is not None:
                        settings = project_settings
                    if defaults is not None:
                        if settings is not None:
                            settings.update(defaults)
                        else:
                            settings = defaults

                    station, datum = split_source(settings['source'])
                    if station != self.name or datum not in self.datums():
                        continue

                    if self.clients is None:
                        self.clients = dict()
                    if project not in self.clients:
                        self.clients[project] = dict()

                    self.clients[project][datum] = {
                        'sensor': sensor,
                        'settings': settings,
                        'safe': False,
                        'reasons': []
                    }

            # process the non-project-specific sensors
            sensors = list(cfg.data['sensors'].keys())
            for sensor in sensors:
                settings = cfg.get(f"sensors.{sensor}")

                station, datum = split_source(settings['source'])
                if station != self.name or datum not in self.datums():
                    continue

                if self.clients is None:
                    self.clients = dict()
                if 'default' not in self.clients:
                    self.clients['default'] = dict()

                self.clients['default'][datum] = {
                    'sensor': sensor,
                    'settings': settings,
                    'safe': False,
                    'reasons': []
                }

        nreadings = 1
        for project in self.clients.keys():
            for sensor in self.clients[project].keys():
                settings = self.clients[project][sensor]['settings']
                nreadings = max(nreadings, settings['nreadings'])
        self.logger.info(f"Allocating a {nreadings} deep fifo")
        self.readings = FixedSizeFifo(nreadings)

        if hasattr(self, 'fetcher'):
            self.thread.start()

    def __del__(self):
        self.stop_event.set()

    def fetcher_loop(self):
        while not self.stop_event.is_set():
            start_time = time.time()
            self.fetcher()
            self.calculate_sensors()
            end_time = time.time()
            # sleep until end of interval
            remaining_time = self.interval - (end_time - start_time)
            time.sleep(remaining_time)

    def latest(self, datum: str, n: int = 1):
        if datum not in self.readings:
            keys = ", ".join(self.readings.data.keys())
            raise f"Bad datum '{datum}', must be one of {keys}"
        max_size = self.readings.max_size
        curr_size = len(self.readings.data)
        if n > curr_size:
            raise (f"station '{self.name}': not enough readings: wanted={n}, " +
                   f"got only {curr_size} out of max={max_size}")

        with self.lock:
            current = [self.readings.data[k] for k in self.readings.data.keys() if k == datum]

        return current[curr_size-1-n:curr_size-1]

    def all_readings(self) -> FixedSizeFifo:
        return self.readings

    def calculate_sensors(self):
        pass


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

    def fetcher(self) -> None:
        pass

    def saver(self, reading: Reading) -> None:
        pass
