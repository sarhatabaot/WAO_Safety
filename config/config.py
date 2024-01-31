import logging
from typing import List, Dict
from copy import deepcopy

import tomlkit

from init_log import init_log
from sensor import Sensor, MinMaxSettings, HumanInterventionSettings, SunElevationSettings
from utils import split_source, SunElevationSensorName, HumanInterventionSensorName

logger: logging.Logger = logging.getLogger('config')
init_log(logger)


class StationSettings:
    enabled: bool
    interval: int  # seconds
    interface: str
    baud: int
    host: str
    port: int
    nreadings: int

    def __init__(self, d: dict):
        self.enabled = d['enabled'] if 'enabled' in d else False
        self.interface = d['interface'] if 'interface' in d else None
        self.baud = d['baud'] if 'baud' in d else None
        self.interval = d['interval'] if 'interval' in d else 60
        self.host = d['host'] if 'host' in d else None
        self.port = d['port'] if 'port' in d else None
        self.nreadings = d['nreadings'] if 'nreadings' in d else 1


class StationConfig:
    name: str
    settings: StationSettings


class LocationConfig:
    longitude: float
    latitude: float
    elevation: float

    def __init__(self, d: dict):
        self.longitude = d['longitude']
        self.latitude = d['latitude']
        self.elevation = d['elevation']


class ServerConfig:
    host: str
    port: int

    def __init__(self, d: dict):
        self.host = d['host']
        self.port = d['port']


class DatabaseConfig:
    host: str
    name: str
    user: str
    password: str
    schema: str

    def __init__(self, d: dict):
        self.host = d['host']
        self.name = d['name']
        self.user = d['user']
        self.password = d['password']
        self.schema = d['schema']


class Config:
    filename: str
    toml: dict
    projects: List[str]
    stations: Dict[str, StationSettings]
    enabled_stations: List[str]
    sensors: Dict[str, List[Sensor]]
    enabled_sensors: List[str]
    stations_in_use: List[str]
    database: DatabaseConfig
    location: LocationConfig
    server: ServerConfig

    def __init__(self):
        self.projects = list()
        self.stations = dict()
        self.sensors = {'default': list()}
        self.stations_in_use = list()
        self.toml = {}
        self.enabled_stations = list()
        # self.filename = '/home/ocs/python/WeatherSafety/config/safety.toml'
        self.filename = 'config/safety.toml'

        with open(self.filename, 'r') as file:
            self.toml = deepcopy(tomlkit.load(file))

        self.database = DatabaseConfig(self.toml['database'])
        self.server = ServerConfig(self.toml['server'])
        self.location = LocationConfig(self.toml['location'])

        for name in list(self.toml['stations'].keys()):
            self.stations[name] = StationSettings(self.toml['stations'][name])

        for key in self.stations.keys():
            if self.stations[key].enabled:
                self.enabled_stations.append(key)

        for ll in [self.stations.keys(), self.enabled_stations, self.stations_in_use]:
            if 'internal' not in ll:
                ll.insert(0, 'internal')

        self.projects = self.toml['global']['projects']
        for project_name in self.projects:
            self.sensors[project_name] = list()

        for sensor_name in self.toml['sensors']:
            # scan the default sensors
            settings_dict = self.toml['sensors'][sensor_name]
            enabled = settings_dict['enabled'] if 'enabled' in settings_dict else False
            if not enabled:
                logger.info(f"project 'default': skipping '{sensor_name}' (not enabled)")
                continue
            station_name, datum = split_source(settings_dict['source'])
            settings_dict['station'] = station_name
            settings_dict['datum'] = datum
            if station_name not in self.enabled_stations:
                logger.info(f"project: 'default': skipping '{sensor_name}' (station '{station_name}' not enabled)")
                continue

            if sensor_name == SunElevationSensorName:
                settings = SunElevationSettings(settings_dict)
            elif sensor_name == HumanInterventionSensorName:
                settings = HumanInterventionSettings(settings_dict)
            else:
                settings = MinMaxSettings(settings_dict)

            settings.project = 'default'
            new_sensor = Sensor(
                name=sensor_name,
                settings=settings,
            )
            logger.info(f"project: 'default', adding '{new_sensor.name}'")
            self.sensors['default'].append(new_sensor)

        # copy all default sensors to the projects
        for project in self.projects:
            self.sensors[project] = deepcopy(self.sensors['default'])
            for s in self.sensors[project]:
                s.settings.project = project

        # look for project-specific sensors and override them
        for project in self.projects:
            if project in self.toml and 'sensors' in self.toml[project]:
                for sensor_name in self.toml[project]['sensors']:
                    project_dict = self.toml[project]['sensors'][sensor_name]
                    sensor = [s for s in self.sensors[project] if s.name == sensor_name]
                    if len(sensor) > 0:  # this sensor is one of the default sensors
                        sensor = sensor[0]
                        sensor.settings.__dict__.update(project_dict)
                        if sensor.settings.station not in self.enabled_stations:
                            sensor.settings.enabled = False
                    else:  # this sensor is defined for this project only
                        if sensor_name == SunElevationSensorName:
                            settings = SunElevationSettings(project_dict)
                        elif sensor_name == HumanInterventionSensorName:
                            settings = HumanInterventionSettings(project_dict)
                        else:
                            settings = MinMaxSettings(project_dict)
                        self.sensors[project].append(
                            Sensor(name=project_dict['name'], settings=settings))

        # make a list of all the station which are enabled and used by at least one sensor
        for project in ['default'] + self.projects:
            for s in self.sensors[project]:
                if not s.settings.enabled:
                    continue
                if s.settings.station not in self.enabled_stations:
                    s.settings.enabled = False
                    continue
                if s.settings.station not in self.stations_in_use:
                    self.stations_in_use.append(s.settings.station)
        self.dump()

    def dump(self):
        print("")
        print("stations:")
        print(f"  all:     {list(self.stations.keys())}")
        print(f"  enabled: {self.enabled_stations}")
        print(f"  in use:  {self.stations_in_use}")
        print("")
        print("sensors (per project):")
        print("")
        for project in ['default'] + self.projects:
            for sensor in self.sensors[project]:
                print(f"  {project:8s} {sensor}")
            print()


cfg = Config()

if __name__ == "__main__":
    cfg.dump()
