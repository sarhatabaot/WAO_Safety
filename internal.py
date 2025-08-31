import datetime
from enum import Enum
from typing import List
import os

from astropy.coordinates import get_sun, AltAz
from astropy.time import Time
from astropy import units as u
from astropy.coordinates import EarthLocation

from config.config import make_cfg
from station import Station, StationReading
from sensor import Sensor, SensorReading
from utils import HumanIntervention, SafetyResponse


class InternalDatum(str, Enum):
    SunElevation = "sun-elevation"
    HumanIntervention = "human-intervention"


class Internal(Station):

    latitude: float
    longitude: float
    elevation: float
    human_intervention_file: HumanIntervention

    def __init__(self, name: str):
        self.name = name
        cfg = make_cfg()

        super().__init__(name=self.name)
        location = cfg.location
        self.latitude = location.latitude
        self.longitude = location.longitude
        self.elevation = location.elevation
        self.human_intervention_file = HumanIntervention(cfg.toml['stations']['internal']['human-intervention-file'])

    def datums(self) -> List[str]:
        return list(InternalDatum.__members__.keys())

    def fetcher(self) -> None:
        pass

    def saver(self, reading: StationReading) -> None:
        pass

    def latest_readings(self, datum: str, n: int = 1) -> list:

        sensor_reading = SensorReading()
        sensor_reading.time = datetime.datetime.now()

        if datum == InternalDatum.SunElevation:
            now = Time.now()
            my_location = EarthLocation(lat=self.latitude * u.deg,
                                        lon=self.longitude * u.deg,
                                        height=self.elevation * u.m)

            # Get the Sun's position in the sky
            alt_az = AltAz(obstime=now, location=my_location)
            sun_position = get_sun(now).transform_to(alt_az)

            # return elevation of the sun
            sensor_reading.value = sun_position.alt.value
            return [sensor_reading]

        elif datum == InternalDatum.HumanIntervention:
            sensor_reading.value = 1 if os.path.exists(self.human_intervention_file.filename) else 0
            return [sensor_reading]
        
    def is_safe(self, sensor: Sensor) -> SafetyResponse:
        response = SafetyResponse(safe=True)
        if sensor.settings.datum == InternalDatum.SunElevation:
            if not (hasattr(sensor.settings, 'dawn') and hasattr(sensor.settings, 'dusk')):
                raise Exception(f"Missing 'dusk' or 'dawn' in {sensor.settings}")
            elevation = self.latest_readings(InternalDatum.SunElevation)
            elevation = elevation[0].value
            current_hour = datetime.datetime.now().hour

            msg = f"sensor 'sun': "
            if current_hour >= 12 and elevation > sensor.settings.dusk:  # PM
                response.safe = False
                response.reasons.append(msg + f"elevation {elevation:.2f} [deg] is " +
                                        f"higher than the dusk (PM) elevation setting ({sensor.settings.dusk:.2f} [deg])")

            if current_hour < 12 and elevation > sensor.settings.dawn:  # AM
                response.safe = False
                response.reasons.append(msg + f"elevation {elevation:.2f} [deg] is " +
                                        f"higher than the dawn (AM) elevation setting ({sensor.settings.dawn:.2f} [deg])")

            return response

        elif sensor.settings.datum == InternalDatum.HumanIntervention:
            return self.human_intervention_file.is_safe()


if __name__ == "__main__":
    internal = Internal(name='internal')
    import time

    for _ in range(5):
        print(f"elevation: {internal.latest_readings('sun-elevation')}, sleeping 30 ...")
        time.sleep(30)
