import datetime
from utils import cfg
from typing import Dict, List
from config.config import split_source


class SensorSettings:
    project: str
    source: str
    min: float
    max: float
    settling: float
    nreadings: int
    station: str
    datum: str
    was_safe: bool = False
    became_safe: datetime.datetime = None

    def __init__(self, d: dict):
        self.project = d['project'] if 'project' in d else "default"
        self.source = d['source'] if 'source' in d else None
        self.min = d['min'] if 'min' in d else 0
        self.max = d['max'] if 'max' in d else None
        self.nreadings = d['nreadings'] if 'nreadings' in d else 1
        self.source = d['source'] if 'source' in d else None
        self.settling = d['settling'] if 'settling' in d else None
        if self.source is not None:
            self.station, self.datum = split_source(self.source)


class Reading:
    datum: float
    time: datetime.datetime


class SafetyResponse:
    """
    The response from a **Sensor** when asked if it is is_safe
    """
    safe: bool          # Is it is_safe?
    reasons: List[str]  # Why it is *unsafe*

    def __init__(self, safe: bool = True, reasons: List[str] = None):
        self.safe = safe
        self.reasons = reasons


class Sensor:
    """
    A **Sensor** is expected to produce a *is_safe*/*unsafe* decision at any given time

    Different projects may have different settings for the sensor, in terms of:

    * **source** - where does the sensor get the readings from (**station**:**datum**)
    * **nreadings** - how many of the latest readings are needed for the decision
    * **min**, **max** - the range in which a reading is considered *is_safe*
    * **settling** - settling time [seconds] during which the sensor remains *unsafe* after all the relevant readings have become *is_safe*
    """

    # station: Station
    enabled: bool = False
    settings: SensorSettings

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

        # station = [s for s in stations if s.name == station]
        # if station is None:
        #     raise f"Cannot find station named '{station}' in stations"

        # station = station[0]
        # datum_names = station.datums()
        # if datum not in datum_names:
        #     raise msg + f"Datum '{datum} is not one of the datums for station '{station}'"

        self.settings[project].source = source
        # self.settings[project].station = station
        self.settings[project].datum = datum_name

    def is_safe(self, project="default") -> SafetyResponse:
        setting = self.settings[project]
        out_of_range = f"out of range min={setting.min}, max={setting.max}"

        try:
            readings = setting.station.latest(setting.datum, setting.nreadings)
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
            # it is actually is_safe, but is it settling?
            if setting.became_safe is not None:
                td = datetime.datetime.now() - setting.became_safe
                if td.seconds > setting.settling:
                    # no bad readings (is_safe) and enough time passed since it became_safe, we're good
                    setting.became_safe = None
                    setting.was_safe = True
                    return SafetyResponse()
                else:
                    td = datetime.timedelta(seconds=setting.settling) - td
                    return SafetyResponse(False, [f"settling ({td} out of {setting.settling} to go)"])
        else:   # some bad readings
            if setting.was_safe:
                setting.was_safe = False
            return SafetyResponse(False, [f"{bad_readings} readings are " + out_of_range])
