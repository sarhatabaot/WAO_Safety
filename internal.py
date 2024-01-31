import datetime
from enum import Enum
from typing import List
import os

from astropy.coordinates import get_sun, AltAz
from astropy.time import Time
from astropy import units as u
from astropy.coordinates import EarthLocation

from config.config import cfg
from station import Station, Reading
from sensor import SensorSettings
from utils import HumanIntervention


class InternalDatum(str, Enum):
    SunElevation = "sun-elevation"
    HumanIntervention = "human-intervention"


class Internal(Station):

    latitude: float
    longitude: float
    elevation: float
    human_intervention: HumanIntervention

    def __init__(self, name: str):
        self.name = name
        super().__init__(name=self.name)
        location = cfg.location
        self.latitude = location.latitude
        self.longitude = location.longitude
        self.elevation = location.elevation
        self.human_intervention = HumanIntervention()

    def datums(self) -> List[str]:
        return list(InternalDatum.__members__.keys())

    def fetcher(self) -> None:
        pass

    def saver(self, reading: Reading) -> None:
        pass

    def latest(self, datum: str, n: int = 1):

        if datum == InternalDatum.SunElevation:
            now = Time.now()
            my_location = EarthLocation(lat=self.latitude * u.deg,
                                        lon=self.longitude * u.deg,
                                        height=self.elevation * u.m)

            # Get the Sun's position in the sky
            alt_az = AltAz(obstime=now, location=my_location)
            sun_position = get_sun(now).transform_to(alt_az)

            # return elevation of the sun
            return sun_position.alt.value

        elif datum == InternalDatum.HumanIntervention:
            return os.path.exists(human_intervention_file)
        
    def is_safe(self, value, settings) -> bool:
        if settings.datum == InternalDatum.SunElevation:
            if not (hasattr(settings, 'dawn') and hasattr(settings, 'dusk')):
                raise Exception(f"Missing 'dusk' or 'dawn' in {settings}")
            elevation = self.latest(InternalDatum.SunElevation)
            hour = datetime.datetime.now().hour
            if hour >= 12:
                return elevation >= settings.dusk
            else:
                return elevation < settings.dawn

        elif settings.datum == InternalDatum.HumanIntervention:
            return self.human_intervention.is_safe()


if __name__ == "__main__":
    internal = Internal(name='internal')
    import time

    for _ in range(5):
        print(f"elevation: {internal.latest('sun-elevation')}, sleeping 30 ...")
        time.sleep(30)
