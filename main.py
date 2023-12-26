import time
import threading
from enum import Enum
from typing import Dict, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, APIRouter

from serial_weather_device import SerialWeatherDevice
from db_access import DbManager
from weather_device import WeatherDevice, DeviceName, DeviceType, get_device_type

from weather_measurement import WeatherMeasurement
from weather_parameter import WeatherParameter


db_manager = DbManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_manager.connect()
    db_manager.open_session()
    init_monitoring()
    yield
    db_manager.close_session()
    db_manager.disconnect()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


weatherRouter = APIRouter(prefix="/weather")


@weatherRouter.get("/raw_data")
async def get_raw_data():
    return weatherMonitor.get_all_measurement()


@weatherRouter.get("measurements/{param}")
async def get_param(param: WeatherParameter):
    data = dict()
    
    for device, measurement in weatherMonitor.get_all_measurement().items():
        value = measurement.get_parameter(param)

        if value is not None:
            data[device] = {param: value, "timestamp": measurement.get_timestamp()}

    return data


class Project(str, Enum):
    Last = "last"
    Mast = "mast"


safetyRouter = APIRouter(prefix="/safety")


@safetyRouter.get("/{project}")
async def get_safety(project: Project):
    return {"is_safe": True}


app.include_router(weatherRouter)
app.include_router(safetyRouter)

control_router = APIRouter(prefix="/control")


@control_router.get("/devices")
async def list_devices():
    return weatherMonitor.list_active_devices()


class WeatherMonitor:
    def __init__(self,
                 device_names: List[DeviceName],
                 saving: Dict[DeviceName, callable] = None):
        self.saving = saving

        self.active_devices: Dict[DeviceName, WeatherDevice] = dict()

        self.last_measurements_lock = threading.Lock()
        self.last_measurements: Dict[DeviceName, WeatherMeasurement] = dict()

        for device_name in device_names:
            if get_device_type(device_name) == DeviceType.SERIAL:
                device = SerialWeatherDevice.connect_device(device_name)

                if device is not None:
                    self.active_devices[device_name] = device

    def make_measurements(self) -> None:
        for device_name, device in self.active_devices.items():
            measurement = device.measure_all()

            with self.last_measurements_lock:
                self.last_measurements[device_name] = measurement

            print(f"Made {device_name} measurement:")
            print(measurement)

    def save_measurements(self):
        if self.saving is not None:
            with self.last_measurements_lock:
                for device_name, save_function in self.saving.items():
                    measurement = self.last_measurements.get(device_name)

                    if measurement is not None:
                        save_function(measurement)

    def list_active_devices(self):
        return list(self.active_devices.keys())

    def get_last_measurement(self, device: DeviceName):
        with self.last_measurements_lock:
            return self.last_measurements.get(device)

    def get_all_measurement(self) -> Dict[DeviceName, WeatherMeasurement]:
        return self.last_measurements.copy()


def save_vantage_measurement(measurement):
    db_manager.write_vantage_measurement(measurement)


def save_arduino_in_measurement(measurement):
    db_manager.write_arduino_in_measurement(measurement)


def save_arduino_out_measurement(measurement):
    db_manager.write_arduino_out_measurement(measurement)


weatherMonitor = WeatherMonitor([DeviceName.DAVIS_VANTAGE, DeviceName.ARDUINO_IN, DeviceName.ARDUINO_OUT],
                                {DeviceName.DAVIS_VANTAGE: save_vantage_measurement,
                                 DeviceName.ARDUINO_IN: save_arduino_in_measurement,
                                 DeviceName.ARDUINO_OUT: save_arduino_out_measurement})


continue_loop_event = threading.Event()
stay_alive_event = threading.Event()


def monitor_weather(dont_pause: threading.Event, dont_stop: threading):
    while dont_stop.is_set():
        print("MONITORING")
        while dont_pause.wait():
            weatherMonitor.make_measurements()
            weatherMonitor.save_measurements()

            time.sleep(30)

        print("MONITORING PAUSED")

    print("MONITORING KILLED")


def init_monitoring():
    continue_loop_event.clear()
    stay_alive_event.set()

    thread = threading.Thread(target=monitor_weather, args=(continue_loop_event, stay_alive_event))
    thread.start()


def continue_monitoring():
    continue_loop_event.set()


def pause_monitoring():
    continue_loop_event.clear()


def kill_monitoring():
    stay_alive_event.clear()
