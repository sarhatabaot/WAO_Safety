import json
import os.path
from threading import Timer, Event
import datetime
from json import JSONEncoder
from fastapi.responses import JSONResponse
from typing import Any, NamedTuple
from enum import Enum

default_port = 8000
Never = datetime.datetime.min

SunElevationSensorName = "sun-sensor"
HumanInterventionSensorName = "human-intervention"


class RepeatTimer(Timer):
    def __init__(self, name, interval, function):
        super(RepeatTimer, self).__init__(interval=interval, function=function)
        self.name = name
        self.interval = interval
        self.function = function
        self.stopped = Event()

    def run(self):
        while not self.stopped.wait(self.interval):
            self.function(*self.args, **self.kwargs)

    def stop(self):
        self.stopped.set()


class FixedSizeFifo:
    def __init__(self, max_size: int):
        self.max_size = max_size
        self.data = []

    def push(self, item):
        if len(self.data) >= self.max_size:
            self.data.pop(0)
        self.data.append(item)

    def latest(self):
        return self.data[0]

    def get(self):
        return self.data


# class SingletonFactory:
#     _instances = {}
#     _lock = Lock()  # A lock for synchronizing instance creation
#
#     @classmethod
#     def get_instance(cls, class_type, *args, **kwargs):
#         with cls._lock:
#             if class_type not in cls._instances:
#                 cls._instances[class_type] = class_type(*args, **kwargs)
#         return cls._instances[class_type]


class DateTimeEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        # Let the base class default method raise the TypeError
        return JSONEncoder.default(self, obj)


def datetime_decoder(dct):
    for key, value in dct.items():
        if isinstance(value, str):
            try:
                dct[key] = datetime.datetime.fromisoformat(value)
            except ValueError:
                pass  # Not a datetime string, so we leave it unchanged
    return dct


class ExtendedJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return json.dumps(content, default=DateTimeEncoder).encode('utf-8')


class Source(NamedTuple):
    station: str
    datum: str


def split_source(source: str) -> NamedTuple:
    s = source.split(':')
    return Source(s[0], s[1])


class Singleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Singleton, cls).__new__(cls)
        return cls._instance


class SingletonFactory:
    _instances = {}

    def __new__(cls, class_type, *args, **kwargs):
        if class_type not in cls._instances:
            instance = super().__new__(class_type)
            class_type.__init__(instance, *args, **kwargs)
            cls._instances[class_type] = instance
        return cls._instances[class_type]


class Reading:
    datums: dict
    tstamp: datetime.datetime

    def __init__(self):
        self.datums = dict()


class VantageProDatum(str, Enum):
    Barometer = "barometer",
    InsideTemperature = "inside_temperature",
    InsideHumidity = "inside_humidity",
    OutsideTemperature = "outside_temperature",
    WindSpeed = "wind_speed",
    WindDirection = "wind_direction",
    OutSideHumidity = "outside_humidity",
    RainRate = "rain_rate",
    UV = "uv",
    SolarRadiation = "solar_radiation",

    @classmethod
    def datums(cls):
        return [item.value for item in cls]


class VantageProReading(Reading):
    def __init__(self):
        super().__init__()
        for name in VantageProDatum.datums():
            self.datums[name] = None


class OutsideArduinoDatum(str, Enum):
    TemperatureOut = "temperature_out",
    HumidityOut = "humidity_out",
    PressureOut = "pressure_out",
    DewPoint = "dew_point",
    VisibleLuxOut = "visible_lux_out",
    IrLuminosity = "ir_luminosity",
    WindSpeed = "wind_speed",
    WindDirection = "wind_direction",

    @classmethod
    def names(cls) -> list:
        return [item.value for item in cls]


class OutsideArduinoReading(Reading):
    def __init__(self):
        super().__init__()
        for name in OutsideArduinoDatum.names():
            self.datums[name] = None


class InsideArduinoDatum(str, Enum):
    TemperatureIn = "temperature_in",
    PressureIn = "pressure_in",
    VisibleLuxIn = "visible_lux_in",
    Presence = "presence",
    Flame = "flame",
    CO2 = "co2",
    RawH2 = "raw_h2",
    RawEthanol = "raw_ethanol",
    VOC = "voc",

    @classmethod
    def names(cls) -> list:
        return [item.value for item in cls]


class InsideArduinoReading(Reading):
    def __init__(self):
        super().__init__()
        for name in InsideArduinoDatum.names():
            self.datums[name] = None


class HumanIntervention:
    filename: str

    def __init__(self):
        self.filename = '/home/ocs/python/WeatherSafety/config/human_intervention.json'

    def is_safe(self):
        return os.path.exists(self.filename)

    def create(self, reason: str):
        with open(self.filename, 'w') as file:
            file.write(json.dumps({
                'tstamp': datetime.datetime.now(),
                'reason': reason
            }, indent=2))

    def delete(self):
        os.unlink(self.filename)
