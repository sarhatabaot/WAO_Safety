from enum import Enum
from typing import List
import os

from astropy.coordinates import get_sun, AltAz
from astropy.time import Time
from astropy import units as u
from astropy.coordinates import EarthLocation

from config.config import cfg
from station import Station, Reading, Sensor


class InternalDatum(str, Enum):
    SunElevation = "sun-elevation"
    HumanIntervention = "human-intervention"


human_intervention_file = 'config/intervention.json'


class Internal(Station):

    latitude: float
    longitude: float
    elevation: float

    def __init__(self, name: str):
        self.name = name
        super().__init__(name=self.name)
        location = cfg.get('location')
        self.latitude = location['latitude']
        self.longitude = location['longitude']
        self.elevation = location['elevation']

    def datums(self) -> List[str]:
        return list(InternalDatum.__members__.keys())

    # def start(self):
    #     for datum in [member.value for member in InternalDatum]:
    #         new_sensor = Sensor(
    #             name=datum,
    #             project='default',
    #             datum=datum,
    #             default_settings=SensorSettings(d),
    #             station=self,
    #         )

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
        
    # def start(self):
    #     pass


if __name__ == "__main__":
    internal = Internal(name='internal')
    import time

    for _ in range(5):
        print(f"elevation: {internal.latest('sun-elevation')}, sleeping 30 ...")
        time.sleep(30)
