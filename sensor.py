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
    was_safe: bool
    became_safe: datetime.datetime

    def __init__(self, d: dict):
        self.enabled = d['enabled'] if 'enabled' in d else False
        self.project = d['project'] if 'project' in d else "default"
        self.source = d['source'] if 'source' in d else None
        if self.source is not None:
            self.station, self.datum = split_source(self.source)
        self.became_safe = Never
        self.was_safe = False

    def __repr__(self):
        return f"{self.__dict__}"


class HumanInterventionSettings(SensorSettings):
    human_intervention_file: str

    def __init__(self, d: dict):
        super().__init__(self, d)
        self.human_intervention_file = d['human-intervention-file'] \
            if 'human-intervention-file' in d else None


class SunElevationSettings(SensorSettings):
    dusk: float  # [degrees]
    dawn: float  # [degrees]

    def __init__(self, d: dict):
        super().__init__(self, d)
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
    name: str
    previous_reading_was_safe: bool = False
    became_safe: datetime.datetime = Never
    reasons: List[str]
    settings: SensorSettings
    station: Any
    safe: bool = False

    def __init__(self,
                 name: str,
                 settings: SensorSettings):
        self.name = name
        self.previous_reading_was_safe = False
        self.settings = settings
        self.reasons = []
        if hasattr(settings, 'settling') and settings.settling is not None:
            self.settling_delta = td(seconds=settings.settling)

    def __repr__(self):
        return f"Sensor(name='{self.name}', settings={self.settings}"

    def has_settled(self) -> bool:
        """
        Checks if the sensor's settling period has ended
        :return:
        """
        needed_settling = (datetime.datetime.now() - self.became_safe)
        if needed_settling <= self.settling_delta:
            self.reasons.append(f"Is settling, for {needed_settling} more")
            return False
        else:
            self.station.logger.info(f"'{self.name}' ended settling period")
            self.became_safe = Never
            return True
