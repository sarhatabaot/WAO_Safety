import logging
import os.path
from typing import List, Dict
from copy import deepcopy

import tomlkit

from init_log import init_log
from sensor import Sensor, SensorSettings
from station import StationSettings
from utils import split_source


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

    def __init__(self, d):
        self.host = d['host']
        self.name = d['name']
        self.user = d['user']
        self.password = d['password']
        self.schema = d['schema']


class Config:
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
        self.database = DatabaseConfig({})
        self.location = LocationConfig({})
        self.server = ServerConfig({})


cfg = Config()

logger: logging.Logger = logging.getLogger('config')
init_log(logger)


def initialize():
    global cfg

    with open(os.path.realpath('../config/safety.toml'), 'r') as file:
        cfg.toml = deepcopy(tomlkit.load(file))

    cfg.database = DatabaseConfig(cfg.toml['database'])
    for name in list(cfg.toml['stations'].keys()):
        cfg.stations[name] = StationSettings(cfg.toml['stations'][name])

    for key in cfg.stations.keys():
        if cfg.stations[key].enabled:
            cfg.enabled_stations.append(key)

    for ll in [cfg.stations.keys(), cfg.enabled_stations, cfg.stations_in_use]:
        if 'internal' not in ll:
            ll.insert(0, 'internal')

    cfg.projects = cfg.toml['global']['projects']
    for project_name in cfg.projects:
        cfg.sensors[project_name] = list()

    for sensor_name in cfg.toml['sensors']:
        # scan the default sensors
        settings_dict = cfg.toml['sensors'][sensor_name]
        enabled = settings_dict['enabled'] if 'enabled' in settings_dict else False
        if not enabled:
            logger.info(f"project 'default': skipping '{sensor_name}' (not enabled)")
            continue
        station_name, datum = split_source(settings_dict['source'])
        settings_dict['station'] = station_name
        settings_dict['datum'] = datum
        if station_name not in cfg.enabled_stations:
            logger.info(f"project: 'default': skipping '{sensor_name}' (station '{station_name}' not enabled)")
            continue

        settings = SensorSettings(settings_dict)
        settings.project = 'default'
        new_sensor = Sensor(
            name=sensor_name,
            settings=settings,
        )
        logger.info(f"project: 'default', adding '{new_sensor.name}'")
        cfg.sensors['default'].append(new_sensor)

    # copy all default sensors to the projects
    for project in cfg.projects:
        cfg.sensors[project] = deepcopy(cfg.sensors['default'])
        for s in cfg.sensors[project]:
            s.settings.project = project

    # look for project-specific sensors and override them
    for project in cfg.projects:
        if project in cfg.toml and 'sensors' in cfg.toml[project]:
            for sensor_name in cfg.toml[project]['sensors']:
                project_dict = cfg.toml[project]['sensors'][sensor_name]
                sensor = [s for s in cfg.sensors[project] if s.name == sensor_name]
                if len(sensor) > 0:  # this sensor is one of the default sensors
                    sensor = sensor[0]
                    sensor.settings.__dict__.update(project_dict)
                    if sensor.settings.station not in cfg.enabled_stations:
                        sensor.settings.enabled = False
                else:   # this sensor is defined for this project only
                    cfg.sensors[project].append(
                        Sensor(name=project_dict['name'],
                               settings=SensorSettings(project_dict)))

    # make a list of all the station which are enabled and used by at least one sensor
    for project in ['default'] + cfg.projects:
        for s in cfg.sensors[project]:
            if not s.settings.enabled:
                continue
            if s.settings.station not in cfg.enabled_stations:
                s.settings.enabled = False
                continue
            if s.settings.station not in cfg.stations_in_use:
                cfg.stations_in_use.append(s.settings.station)


def dump_cfg():
    global cfg

    print(f"stations: {cfg.stations.keys()}")
    print(f"stations in use: {cfg.stations_in_use}")
    print(f"enabled stations: {cfg.enabled_stations}")
    print()
    for project in ['default'] + cfg.projects:
        for sensor in cfg.sensors[project]:
            print(f"{project:6s} {sensor}")
        print()


if __name__ == "__main__":
    initialize()
    dump_cfg()
