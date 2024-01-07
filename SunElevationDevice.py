from typing import List

from astropy.coordinates import get_sun, AltAz
from astropy.time import Time
from astropy import units as u
from astropy.coordinates import EarthLocation

from calculation_device import CalculationDevice
from weather_parameter import WeatherParameter


class SunElevationDevice(CalculationDevice):
    def __init__(self, longitude,  latitude, height):
        super().__init__()

        self.latitude = latitude  # degrees
        self.longitude = longitude  # degrees
        self.height = height  # meters

    def _calculate(self):
        sun_elevation = self._calculate_elevation()
        return {WeatherParameter.SUN_ELEVATION: sun_elevation}

    def _calculate_elevation(self):
        now = Time.now()
        my_location = EarthLocation(lat=self.latitude * u.deg,
                                    lon=self.longitude * u.deg,
                                    height=self.height * u.m)  # Replace with your latitude and longitude

        # Get the Sun's position in the sky
        alt_az = AltAz(obstime=now, location=my_location)
        sun_position = get_sun(now).transform_to(alt_az)

        # return elevation of the sun
        return sun_position.alt

    def list_measurements(self) -> List[WeatherParameter]:
        return [WeatherParameter.SUN_ELEVATION]


