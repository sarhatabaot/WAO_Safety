import datetime
from typing import List, Any
from utils import split_source, Never
from datetime import timedelta as td


class SensorSettings:

    def __init__(self, d: dict):
        self.enabled: bool = d['enabled'] if 'enabled' in d else False
        self.project: str = d['project'] if 'project' in d else "default"
        self.source: str = d['source'] if 'source' in d else None
        self.station: str = None
        self.datum: str = None
        if self.source is not None:
            self.station, self.datum = split_source(self.source)
        # self.became_safe = None

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

    def __init__(self, d: dict):
        SensorSettings.__init__(self, d)
        self.dawn: float = d['dawn'] if 'dawn' in d else None
        self.dusk: float = d['dusk'] if 'dusk' in d else None
        self.nreadings = 1


class MinMaxSettings(SensorSettings):

    def __init__(self, d: dict):
        SensorSettings.__init__(self, d)
        self.min: float = d['min'] if 'min' in d else 0
        self.max: float = d['max'] if 'max' in d else (2 ** 32 - 1)
        self.settling: float = d['settling'] if 'settling' in d else None
        self.nreadings: int = d['nreadings'] if 'nreadings' in d else 1


class SensorReading:

    def __init__(self):
        self.value: float = None
        self.time: datetime = None


class Sensor:

    def __init__(self,
                 name: str,
                 settings: SensorSettings
                 ):
        self.name: str = name
        self.station: str = None
        self.safe: bool = False
        self.settings: SensorSettings = settings
        self.readings: List[SensorReading] = []
        self.reasons_for_not_safe: List[str] = []
        self.started_settling: datetime.datetime = None
        if hasattr(settings, 'settling') and settings.settling is not None:
            self.settling_delta = td(seconds=settings.settling)

    def __repr__(self):
        return f"Sensor(name='{self.name}', settings={self.settings}"
    
    @property
    def values(self) -> List[float]:
        if len(self.readings) == 0:
            return []
        return [reading.value for reading in self.readings]

    def has_settled(self) -> bool:
        """
        Checks if the sensor's settling period has ended
        :return:
        """
        if self.started_settling == None:
            return True

        needed_settling = (datetime.datetime.now() - self.started_settling)
        if needed_settling <= self.settling_delta:
            self.reasons_for_not_safe.append(f"is settling, for {needed_settling} more seconds")
            return False
        else:
            self.station.logger.info(f"'{self.name}' ended settling period")
            self.started_settling = None
            return True

    @property
    def average(self) -> float:
        if isinstance(self.readings, list):
            return sum([r.value for r in self.readings]) / len(self.readings)
        return None
        
    @property
    def values_out_of_range(self) -> int:

        readings = self.readings
        
        if not isinstance(readings, list):
            readings = [readings]
        if len(readings) == 0:
            return 0
        
        try:
            if isinstance(self.settings, SunElevationSettings):
                return 1 if readings[0].value < self.settings.dawn or readings[0].value >= self.settings.dusk else 0
            
            elif isinstance(self.settings, HumanInterventionSettings):
                return 1 if readings[0].value else 0
            else:
                values = [r.value for r in self.readings if r.value < self.settings.min or r.value >= self.settings.max]
                return len(values)
        except TypeError as e:
            print(f"TypeError: {e}")
            print(self)
