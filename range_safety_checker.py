import os.path
from typing import Dict, List

import tomlkit

from device_name import DeviceName
from project import Project
from safety_checker import SafetyChecker
from weather_measurement import WeatherMeasurement
from weather_parameter import WeatherParameter


class ParameterConfig:
    def __init__(self, /, min_value=None, max_value=None, source=None, interval=None, total_time=None):
        self.min_value = min_value
        self.max_value = max_value
        self.source = source
        self.interval = interval
        self.total_time = total_time

    def update(self, other_config):
        if other_config.min_value is not None:
            self.min_value = other_config.min_value

        if other_config.max_value is not None:
            self.max_value = other_config.min_value

        if other_config.source is not None:
            self.source = other_config.source

        if other_config.interval is not None:
            self.interval = other_config.interval

        if other_config.total_time is not None:
            self.total_time = other_config.total_time

    def copy(self):
        return ParameterConfig(min_value=self.min_value,
                               max_value=self.max_value,
                               source=self.source,
                               interval=self.interval,
                               total_time=self.total_time)

    @staticmethod
    def empty_config():
        return ParameterConfig()


class DeviceMeasuringConfig:
    def __init__(self, interval=60, queue_size=1):
        self.interval = interval
        self.queue_size = queue_size


class RangeSafetyChecker(SafetyChecker):
    """
    A safety checker that decides that the weather is safe only if the
    all the parameters are in the specified range for the specifies time.
    If more than one parameter is required from the same device, it chooses the
    minimal measuring interval, and adjusts the queue size such that it will have measurements
    from the maximal total time.
    """
    CONFIG_FOLDER_PATH = "safety_config"

    DEFAULT = "default.toml"

    def __init__(self):
        self.projects_configs: Dict[Project, Dict[WeatherParameter, ParameterConfig]] = dict()
        self._read_config(RangeSafetyChecker.CONFIG_FOLDER_PATH)

        self._device_measuring_config: Dict[DeviceName, DeviceMeasuringConfig] = dict()
        self._init_all_devices_config()

    def _read_config(self, folder_name) -> None:
        """
        Read all configurations
        :param folder_name: name of folder where the files are located
        """

        # Read the default config
        default_config = RangeSafetyChecker._parse_config(os.path.join(folder_name, RangeSafetyChecker.DEFAULT))

        # for each project, update the config according to the project file
        for project_str in Project:
            project = Project(project_str)

            default_copy = {param: config.copy() for param, config in default_config.items()}
            all_parameters_config = RangeSafetyChecker._parse_config(os.path.join(folder_name, f"{project_str}.toml"))

            updated_config = dict()

            for param_str in WeatherParameter:
                param = WeatherParameter(param_str)

                param_config = default_copy.get(param, ParameterConfig.empty_config())
                specific_param_config = all_parameters_config.get(param, ParameterConfig.empty_config())

                param_config.update(specific_param_config)
                updated_config[param] = param_config

            self.projects_configs[project] = updated_config

    @staticmethod
    def _parse_config(filename: str):
        """
        Reads a config file and returns the configs found in it
        :param filename: filename of the config file
        :return: Dictionary of the configurations found in the file
        """
        parameters_config = dict()

        with open(filename, "r") as fp:
            doc = tomlkit.load(fp)

            for param_str in WeatherParameter:
                param = WeatherParameter(param_str)

                if doc.get(param_str) is not None:
                    min_value = doc[param_str].get("min")
                    max_value = doc[param_str].get("max")

                    source_str = doc[param_str].get("source")
                    source = DeviceName(source_str) if source_str is not None else None

                    interval = doc[param_str].get("interval")
                    total_time = doc[param_str].get("total_time")

                    config = ParameterConfig(min_value=min_value,
                                             max_value=max_value,
                                             source=source,
                                             interval=interval,
                                             total_time=total_time)

                    parameters_config[param] = config

        return parameters_config

    def _init_all_devices_config(self):
        for device_str in DeviceName:
            device_name = DeviceName(device_str)

            interval = self._calc_measuring_interval(device_name)
            queue_size = self._calc_queue_size(device_name)

            self._device_measuring_config[device_name] = DeviceMeasuringConfig(interval, queue_size)

    def get_device_measuring_config(self, device: DeviceName):
        return self._device_measuring_config[device]

    def is_safe(self, project: Project, devices_measurements: Dict[DeviceName, List[WeatherMeasurement]]) -> bool:
        """
        Check
        :param devices_measurements: a
        :param project: project
        :return: True if all the measurements are in sage range, False otherwise
        """

        project_config = self.projects_configs[project]

        for parameter, param_config in project_config.items():
            device = param_config.source
            measurements = devices_measurements[device]

            required_count = self._device_measuring_config[device].queue_size

            # Check if there are not enough measurements
            if len(measurements) < required_count:
                return False

            for measurement in measurements:
                value = measurement.get_parameter(parameter)

                # Value is out of range
                if value < param_config.min_value or value > param_config.max_value:
                    return False

        return True

    def _calc_measuring_interval(self, device_name: DeviceName) -> int:
        """
        Calculates the required measuring interval.
        :param device_name: Name of device
        :return: Required interval, or 0 if every interval can be used
        """
        min_interval = 100000

        for project_str in Project:
            project = Project(project_str)

            project_config = self.projects_configs[project]

            for param, config in project_config.items():
                if config.source == device_name and config.interval is not None:
                    min_interval = min(min_interval, config.interval)

        return min_interval if min_interval != 100000 else 0

    def _calc_queue_size(self, device_name: DeviceName) -> int:
        """
        Calculates the required queue size
        :param device_name: Name of device
        :return: Required interval, or 0 if every interval can be used
        """
        interval = self._calc_measuring_interval(device_name)

        max_time = -1

        for project_str in Project:
            project = Project(project_str)

            project_config = self.projects_configs[project]

            for param, config in project_config.items():
                if config.source == device_name and config.total_time is not None:
                    max_time = max(max_time, config.total_time)

        return int(max_time / interval) if max_time != -1 else 0
