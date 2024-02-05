import datetime
from typing import List, Any
from utils import split_source, Never
from datetime import timedelta as td


class SensorSettings:
    enabled: bool
    project: str
    source: str
    station: str
    datum: str
    became_safe: datetime.datetime

    def __init__(self, d: dict):
        self.enabled = d['enabled'] if 'enabled' in d else False
        self.project = d['project'] if 'project' in d else "default"
        self.source = d['source'] if 'source' in d else None
        if self.source is not None:
            self.station, self.datum = split_source(self.source)
        self.became_safe = Never

    def __repr__(self):
        return f"{self.__dict__}"


class HumanInterventionSettings(SensorSettings):
    human_intervention_file: str
    nreadings: int = 1

    def __init__(self, d: dict):
        SensorSettings.__init__(self, d)
        self.human_intervention_file = d['human-intervention-file'] \
            if 'human-intervention-file' in d else None


class SunElevationSettings(SensorSettings):
    dusk: float  # [degrees]
    dawn: float  # [degrees]
    nreadings: int = 1

    def __init__(self, d: dict):
        SensorSettings.__init__(self, d)
        self.dawn = d['dawn'] if 'dawn' in d else None
        self.dusk = d['dusk'] if 'dusk' in d else None


class MinMaxSettings(SensorSettings):
    min: float
    max: float
    settling: float
    nreadings: int

    def __init__(self, d: dict):
        SensorSettings.__init__(self, d)
        self.min = d['min'] if 'min' in d else 0
        self.max = d['max'] if 'max' in d else (2 ** 32 - 1)
        self.settling = d['settling'] if 'settling' in d else None
        self.nreadings = d['nreadings'] if 'nreadings' in d else 1


class Reading:
    datum: float
    time: datetime.datetime


class Sensor:
    name: str
    started_settling: datetime.datetime = Never
    reasons: List[str]
    settings: SensorSettings
    station: Any
    safe: bool = False
    values: List[float]
    # id: int

    def __init__(self,
                 name: str,
                 settings: SensorSettings):
        # self.id = id(self)
        self.name = name
        self.settings = settings
        self.values = list()
        self.reasons = list()
        if hasattr(settings, 'settling') and settings.settling is not None:
            self.settling_delta = td(seconds=settings.settling)

    def __repr__(self):
        return f"Sensor(name='{self.name}', settings={self.settings}"

    def has_settled(self) -> bool:
        """
        Checks if the sensor's settling period has ended
        :return:
        """
        if self.started_settling == Never:
            return True

        needed_settling = (datetime.datetime.now() - self.started_settling)
        if needed_settling <= self.settling_delta:
            self.reasons.append(f"is settling, for {needed_settling} more seconds")
            return False
        else:
            self.station.logger.info(f"'{self.name}' ended settling period")
            self.started_settling = Never
            return True

    def values_out_of_range(self, values=None) -> int:
        # check if the supplied (or existing) values are in range
        if not hasattr(self.settings, 'nreadings'):
            return 0

        if values is None:
            values = self.values

        if isinstance(self.settings, SunElevationSettings):
            return 0  # TBD
        elif isinstance(self.settings, HumanInterventionSettings):
            return 0  # TBD
        elif isinstance(self.settings, MinMaxSettings):

            if isinstance(values, (int, float)):
                return values < self.settings.min or values >= self.settings.max

            if len(self.values) != self.settings.nreadings:
                return 0

            bad = 0
            for v in values:
                if v < self.settings.min or v >= self.settings.max:
                    bad = bad + 1

            return bad
