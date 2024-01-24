import datetime
from utils import Never
from typing import List, Any
from utils import split_source
from datetime import timedelta as td


class SensorSettings:
    enabled: bool
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
        self.enabled = d['enabled'] if 'enabled' in d else False

    def __repr__(self):
        return f"{self.__dict__}"


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
