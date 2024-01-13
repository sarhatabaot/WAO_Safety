import datetime
from abc import ABC, abstractmethod, abstractproperty
from typing import List
from utils import FixedSizeFifo, cfg
from stations import Station
from typing import Dict, List
from collections import namedtuple


class Setting:
    source: str
    min: float
    max: float
    settling: float
    nreadings: int
    station: Station
    datum: str


class Reading:
    datum: float
    time: datetime.datetime


class SafetyResponse:
    """
    The response from a **Sensor** when asked if it is safe
    """
    is_safe: bool       # Is it safe?
    reasons: List[str]  # Why it is *unsafe*


class Sensor:
    """
    A **Sensor** is expected to produce a *safe*/*unsafe* decision at any given time

    Different projects may have different setting for the sensor, in terms of:

    * **source** - where does the sensor get the readings from (**station**:**datum**)
    * **nreadings** - how many of the latest readings are needed for the decision
    * **min**, **max** - the range in which a reading is considered *safe*
    * **settling** - settling time [seconds] during which the sensor remains *unsafe* after all the relevant readings have become *safe*
    """

    station: Station
    enabled: bool = False
    settings: Dict[str, Setting]

    def __init__(self, name: str):
        self.name = name

        self.settings = dict()
        self.settings["default"] = cfg.get(f"sensors.{self.name}")
        self.check_and_set_source(project="default", source=self.settings["default"]['source'])
        for project in cfg.get("global.projects"):
            setting = cfg.get(f"{project}.sensors.{self.name}")
            if setting is not None:
                self.settings[project] = setting

    def check_and_set_source(self, project: str, source: str):
        msg = f"Bad source '{source}' for sensor '{self.name}'  (project='{project}'): "
        if source is None:
            raise msg + "empty"

        src = source.split(":")
        if len(src) != 2:
            raise msg + "Not station:datum"

        station_name = src[0]
        datum_name = src[1]
        station_cfg = cfg.get(f"stations.{station_name}")
        if station_cfg is None:
            raise msg + f"No configuration for station='{station_name}"
        if 'enabled' not in station_cfg or not station_cfg['enabled']:
            raise msg + f"Station '{station_name}' is not enabled"

        datum_names = stations[station_name].datum_names
        if datum_name not in datum_names:
            raise msg + f"Datum '{datum_name} is not one of the datums for station '{station_name}'"

        self.settings[project].source = source
        self.settings[project].station = stations[station_name]
        self.settings[project].datum = datum_name

    @abstractmethod
    def is_safe(self, project=None) -> SafetyResponse:
        pass
