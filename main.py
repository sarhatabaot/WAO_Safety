from typing import Dict, List
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter

from device_manager import DeviceManager
from device_factory import DeviceFactory, DeviceType
from project import Project
from db_access import DbManager
# from weather_device import WeatherDevice
from device_name import DeviceName

from weather_measurement import WeatherMeasurement
from weather_parameter import WeatherParameter

from range_safety_checker import RangeSafetyChecker

db_manager = DbManager()


@asynccontextmanager
async def lifespan(app):
    # db_manager.connect()
    # db_manager.open_session()
    weather_monitor.start_measuring()
    yield
    weather_monitor.stop_measuring()
    db_manager.close_session()
    db_manager.disconnect()

app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Hello World"}


weather_router = APIRouter(prefix="/weather")


@weather_router.get("/raw_data")
async def get_raw_data():
    return weather_monitor.get_all_measurements()


@weather_router.get("/measurements/{param}")
async def get_param(param: WeatherParameter):
    data = dict()

    for device, measurements in weather_monitor.get_all_measurements().items():
        last_measurement = measurements[-1]
        value = last_measurement.get_parameter(param)

        if value is not None:
            data[device] = {param: value, "timestamp": last_measurement.get_timestamp()}

    return data


safety_router = APIRouter(prefix="/safety_config")


@safety_router.get("/{project}")
async def get_safety(project: Project):

    return {"is_safe": range_safety_checker.is_safe(project,
                                                    weather_monitor.get_all_measurements())}


app.include_router(weather_router)
app.include_router(safety_router)

control_router = APIRouter(prefix="/control")


@control_router.get("/devices")
async def list_devices():
    return weather_monitor.list_active_devices()


class WeatherMonitor:
    def __init__(self,
                 device_names: List[DeviceName],
                 saving: Dict[DeviceName, callable] = None,
                 safety_checker=None):

        self.saving = saving
        self.active_device_managers: Dict[DeviceName, DeviceManager] = dict()

        for device_name in device_names:
            if DeviceFactory.get_device_type(device_name) == DeviceType.SERIAL:
                device = DeviceFactory.connect_serial_device(device_name)
            elif DeviceFactory.get_device_type(device_name) == DeviceType.CALCULATION:
                device = DeviceFactory.create_calculation_device(device_name)
            else:
                device = None

            if device is not None:
                measuring_config = safety_checker.get_device_measuring_config(device_name)
                device_manager = DeviceManager(device, measuring_config, self.saving.get(device_name))

                self.active_device_managers[device_name] = device_manager

    def start_measuring(self):
        for device, device_manager in self.active_device_managers.items():
            device_manager.start_measuring()

    def stop_measuring(self):
        for device_manager in self.active_device_managers.values():
            device_manager.stop_measuring()

    def list_active_devices(self):
        return list(self.active_device_managers.keys())

    def get_all_measurements(self) -> Dict[DeviceName, List[WeatherMeasurement]]:
        data = dict()
        for device, manager in self.active_device_managers.items():
            data[device] = manager.get_last_measurements()

        return data


def save_vantage_measurement(measurement):
    db_manager.write_vantage_measurement(measurement)


def save_arduino_in_measurement(measurement):
    db_manager.write_arduino_in_measurement(measurement)


def save_arduino_out_measurement(measurement):
    db_manager.write_arduino_out_measurement(measurement)


ALL_SAVING_FUNCTIONS = {DeviceName.DAVIS_VANTAGE: save_vantage_measurement,
                        DeviceName.ARDUINO_IN: save_arduino_in_measurement,
                        DeviceName.ARDUINO_OUT: save_arduino_out_measurement,
                        DeviceName.SUN_ELEVATION_CALCULATOR: None}

active_devices = DeviceFactory.get_active_devices()
saving_functions = {device: function for device, function in ALL_SAVING_FUNCTIONS.items()
                    if device in active_devices}

range_safety_checker = RangeSafetyChecker()
weather_monitor = WeatherMonitor(active_devices, saving_functions, range_safety_checker)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
