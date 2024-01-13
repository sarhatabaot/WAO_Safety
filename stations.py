import datetime
import logging

from utils import FixedSizeFifo, cfg
from abc import ABC, abstractmethod
from typing import List

from vantage_pro2 import VantagePro2
from inside_arduino import InsideArduino
from outside_arduino import OutsideArduino
import serial
import logging


class Reading:
    data: dict
    tstamp: datetime.datetime


class Datum(ABC):
    @classmethod
    @abstractmethod
    def names(cls):
        pass


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

    @classmethod
    def datum_names(cls) -> List[str]:
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

    def __init__(self, name: str, fetcher: callable = None, saver: callable = None):
        """
        **Station** constructor

        :param name:
            name of the **Station**
        :param fetcher:
            gathers data from the Station
        :param saver:
            saves the Station's data to the database
        """
        configured_stations = cfg.get("stations")
        self.name = name
        if name not in configured_stations:
            raise f"Bad station name '{name}' (not in {configured_stations})"
        self.saver = saver

        #
        # For each of the 'Projects' that have 'Sensors' using this station as their 'source'
        #  get the number of required readings, and allocate a fifo deep enough to store the largest required number.
        #
        projects = cfg.get('global.projects')
        sensors = cfg.data['sensors'].keys()
        requirements = dict()
        this_station = self.name

        for project in projects:
            for sensor in sensors:
                source = cfg.get(f"sensors.{sensor}.source")
                # print(f"sensor='{sensor}', default_source='{source}'")
                project_source: str = cfg.get(f"{project}.sensors.{sensor}.source")
                # print(f" project_source='{project_source}'")
                if project_source is not None:
                    source = project_source
                if source is not None and source.startswith(f"{this_station}:"):
                    datum = source.replace(f"{this_station}:", "")
                    # print(f"  datum='{datum}'")
                    if datum not in requirements:
                        requirements[datum] = list()
                    project_nreadings = cfg.get(f"{project}.sensors.{sensor}.nreadings")
                    if project_nreadings is None:
                        project_nreadings = 1
                    default_nreadings = cfg.get(f"sensors.{sensor}.nreadings")
                    if default_nreadings is None:
                        default_nreadings = 1
                    requirements[datum].append(max(project_nreadings, default_nreadings))

        for datum in requirements.keys():
            nreadings = max(requirements[datum])
            print(f"allocating fifo({nreadings}) for datum '{datum}'")
            self._readings = FixedSizeFifo(nreadings)

    def latest_readings(self, n: int):
        max_size = self._readings.max_size
        if n >= max_size:
            raise f"no {n} readings: station '{self.name}' has {len(self._readings.data)} datums (max={max_size})"
        return self._readings.data[0:n]


class SerialStation:

    def __init__(self, name: str, logger: logging.Logger):

        config = cfg.get(f"stations.{name}")
        if config is None:
            raise f"Cannot get configuration for station='{name}' from '{cfg.filename}'"

        if 'enabled' not in config or not config['enabled']:
            logger.error(f"Station '{name}' not enabled in '{cfg.filename}'")
            return

        if 'interface' not in config.data:
            raise f"Missing 'interface' in configuration for station='{name}' in '{cfg.filename}'"
        if 'baud' not in config:
            raise f"Missing 'baud' in configuration for station='{name}' in '{cfg.filename}'"

        port = config.data['interface']
        baud = config.data['baud']
        try:
            self.ser = serial.Serial(port, baud)
        except Exception as ex:
            logger.error(f"Cannot open serial port '{port}'", exc_info=ex)
            return


stations = {
    'davis': VantagePro2(name='davis'),
    'inside-arduino': InsideArduino(name='inside-arduino'),
    'outside-arduino': OutsideArduino(name='outside-arduino')
}
