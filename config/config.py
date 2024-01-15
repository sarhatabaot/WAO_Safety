import os.path
import tomlkit
from typing import List


class Config:
    data: dict
    filename: str
    stations: List[str]
    enabled_stations: List[str]
    sensors: List[str]
    enabled_sensors: List[str]

    def __init__(self):
        self.filename = os.path.realpath('config/safety.toml')
        with open(self.filename, 'r') as file:
            self.data = tomlkit.load(file)
        self.projects = self._get('global.projects')
        self.stations = list(self.data['stations'].keys())
        self.enabled_stations = [s for s in self.stations if 'enabled' in self.data['stations'][s] and self.data['stations'][s]['enabled']]

        self.stations.insert(0, 'calculator')
        self.enabled_stations.insert(0, 'calculator')

        self.sensors = list()
        self.enabled_sensors = list()
        sensors = list(self.data['sensors'].keys())
        for sensor in sensors:
            source = self.data['sensors'][sensor]['source']
            s = source.split(':')
            if len(s) != 2:
                raise f"Bad source '{source}' for sensor '{sensor}"
            d = {'station': s[0], 'datum': s[1]}
            station = s[0]
            datum = s[1]
            if station in self.enabled_stations:
                self.enabled_sensors.append(sensor)
            self.sensors.append(sensor)

    def validate(self):
        pass

    def _get(self, path: str) -> object:
        defaults = {
            'min': 0,
            'nreadings': 1,
        }
        key = None
        keys = path.split('.')

        try:
            value = self.data
            for key in keys:
                value = value[key]
            return value
        except KeyError:
            return defaults[key] if key in defaults else None

    def get(self, path):
        #
        # Same as self._get(), but allows project-specific sensors to override global sensor definitions
        #
        keys = path.split('.')
        if keys[0] in self.projects and keys[1] == 'sensors':
            project_value = self._get(path)
            global_value = self._get('.'.join(keys[1:]))
            if isinstance(project_value, dict):
                global_value.update(project_value)
                ret = global_value
            else:
                ret = project_value
            return ret
        else:
            return self._get(path)
