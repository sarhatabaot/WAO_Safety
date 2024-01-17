import datetime
from abc import ABC, abstractmethod, abstractproperty
from typing import List
from utils import FixedSizeFifo, cfg
# from station import Station
from typing import Dict, List
# from main import stations


class Setting:
    source: str
    min: float
    max: float
    seconds_for_settling: float
    nreadings: int
    # station: Station
    station_name: str
    datum_name: str
    was_safe: bool = False
    changed_to_safe: datetime.datetime = None


class Reading:
    datum: float
    time: datetime.datetime


class SafetyResponse:
    """
    The response from a **Sensor** when asked if it is safe
    """
    safe: bool       # Is it safe?
    reasons: List[str]  # Why it is *unsafe*

    def __init__(self, safe: bool = True, reasons: List[str] = None):
        self.safe = safe
        self.reasons = reasons


class Sensor:
    """
    A **Sensor** is expected to produce a *safe*/*unsafe* decision at any given time

    Different projects may have different setting for the sensor, in terms of:

    * **source** - where does the sensor get the readings from (**station**:**datum**)
    * **nreadings** - how many of the latest readings are needed for the decision
    * **min**, **max** - the range in which a reading is considered *safe*
    * **settling** - settling time [seconds] during which the sensor remains *unsafe* after all the relevant readings have become *safe*
    """

    # station: Station
    enabled: bool = False
    settings: Dict[str, Setting]

    def __init__(self, name: str):
        self.name = name

        self.settings = dict()
        self.settings["default"] = cfg.get(f"sensors.{self.name}")
        self.check_and_set_source(project="default", source=self.settings["default"]['source'])
        for project in cfg.projects:
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
        if station_name not in cfg.enabled_stations:
            raise msg + f"Station '{station_name}' is not enabled"
        station_cfg = cfg.get(f"stations.{station_name}")
        if station_cfg is None:
            raise msg + f"No configuration for station='{station_name}"

        # station = [s for s in stations if s.name == station_name]
        # if station is None:
        #     raise f"Cannot find station named '{station_name}' in stations"

        # station = station[0]
        # datum_names = station.datums()
        # if datum_name not in datum_names:
        #     raise msg + f"Datum '{datum_name} is not one of the datums for station '{station_name}'"

        self.settings[project].source = source
        # self.settings[project].station = station
        self.settings[project].datum_name = datum_name

    def is_safe(self, project="default") -> SafetyResponse:
        setting = self.settings[project]
        out_of_range = f"out of range min={setting.min}, max={setting.max}"

        try:
            readings = setting.station.latest(setting.datum_name, setting.nreadings)
        except Exception as ex:
            return SafetyResponse(False, [f"{ex}"])

        if setting.nreadings == 1:
            # it's a one-shot sensor, just one relevant reading
            if setting.min <= readings[0] > setting.max:
                return SafetyResponse(False, reasons=[out_of_range])
            else:
                return SafetyResponse()

        bad_readings = 0
        for reading in readings:
            if setting.min < reading >= setting.max:
                bad_readings = bad_readings + 1

        if bad_readings == 0:
            # it is actually safe, but is it settling?
            if setting.changed_to_safe is not None:
                td = datetime.datetime.now() - setting.changed_to_safe
                if td.seconds > setting.seconds_for_settling:
                    # no bad readings (safe) and enough time passed since it changed_to_safe, we're good
                    setting.changed_to_safe = None
                    setting.was_safe = True
                    return SafetyResponse()
                else:
                    td = datetime.timedelta(seconds=setting.seconds_for_settling) - td
                    return SafetyResponse(False, [f"settling ({td} out of {setting.seconds_for_settling} to go)"])
        else:   # some bad readings
            if setting.was_safe:
                setting.was_safe = False
            return SafetyResponse(False, [f"{bad_readings} readings are " + out_of_range])
