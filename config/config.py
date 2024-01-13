import os.path

import tomlkit


class Config:
    data: dict
    filename: str

    def __init__(self):
        self.filename = os.path.realpath('config/safety.toml')
        with open(self.filename, 'r') as file:
            self.data = tomlkit.load(file)
        self.projects = self._get('global.projects')

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
