from enum import Enum
from typing import List

from astropy.coordinates import get_sun, AltAz
from astropy.time import Time
from astropy import units as u
from astropy.coordinates import EarthLocation

from utils import cfg
from stations import Station, Reading


class CalculatorDatum(str, Enum):
    SunElevation = "sun-elevation"


class Calculator(Station):

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
        return list(CalculatorDatum.__members__.keys())

    def fetcher(self) -> None:
        pass

    def saver(self, reading: Reading) -> None:
        pass

    def latest(self, datum: str, n: int = 1):

        if datum == "sun-elevation":
            now = Time.now()
            my_location = EarthLocation(lat=self.latitude * u.deg,
                                        lon=self.longitude * u.deg,
                                        height=self.elevation * u.m)

            # Get the Sun's position in the sky
            alt_az = AltAz(obstime=now, location=my_location)
            sun_position = get_sun(now).transform_to(alt_az)

            # return elevation of the sun
            return sun_position.alt.value
        
    def start(self):
        pass



if __name__ == "__main__":
    calc = Calculator(name='calculator')
    import time

    for _ in range(5):
        print(f"elevation: {calc.latest('sun-elevation')}, sleeping 30 ...")
        time.sleep(30)
