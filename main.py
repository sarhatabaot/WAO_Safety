import time
import threading
from enum import Enum
from typing import Optional, Dict, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, APIRouter
import serial
import serial.tools.list_ports
import tomlkit

from outside_arduino import OutsideArduino
from vantage_pro2 import VantagePro2
from inside_arduino import InsideArduino
from db_access import DbManager
from serial_weather_device import SerialWeatherDevice
from weather_measurement import WeatherMeasurement
from weather_parameter import WeatherParameter
db_manager = DbManager()

com_ports = serial.tools.list_ports.comports()
free_ports = {com_port.device : True for com_port in com_ports}


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


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

@weatherRouter.get("/devices")
async def get_devices():
    return weatherMonitor.list_active_devices()

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


class DeviceName(str, Enum):
    ARDUINO_IN = "arduino_in"
    ARDUINO_OUT = "arduino_out"
    DAVIS_VANTAGE = "davis_vantage"

safetyRouter = APIRouter(prefix="/safety")


@safetyRouter.get("/{project}")
async def get_safety(project: Project):
    return {"is_safe": True}


app.include_router(weatherRouter)
app.include_router(safetyRouter)


class WeatherMonitor:
    def __init__(self, 
                 devices: List[DeviceName], 
                 saving: Dict[DeviceName, callable] = None):
        self.saving = saving

        self.active_devices : Dict[DeviceName, SerialWeatherDevice] = dict()

        self.last_measurements_lock = threading.Lock()
        self.last_measurements: Dict[DeviceName, WeatherMeasurement] = dict()

        self._vantage_last_measurement: Optional[WeatherMeasurement] = None
        self._vantage_measurement_lock = threading.Lock()

        self._arduino_in_last_measurement: Optional[WeatherMeasurement] = None
        self._arduino_in_measurement_lock = threading.Lock()

        self._davis_vantage_lock = threading.Lock()
        self._arduino_in_lock = threading.Lock()

        if DeviceName.DAVIS_VANTAGE in devices:
            print("Inifializing weather devices")
            self._davis_vantage = VantagePro2()
            if not self._connect_device(self._davis_vantage, "VantagePro2"):
                self._davis_vantage = None
            else:
                self.active_devices[DeviceName.DAVIS_VANTAGE] = self._davis_vantage

        if DeviceName.ARDUINO_IN in devices:
            self._inside_arduino = InsideArduino()
            if not self._connect_device(self._inside_arduino, "InsideArduino"):
                self._inside_arduino = None
            else:
                self.active_devices[DeviceName.ARDUINO_IN] = self._inside_arduino

        # self._outside_arduino = OutsideArduino()

    def _connect_device(self, device: SerialWeatherDevice, config_name: str) -> bool:
        print(f"Trying to connect {config_name}")
        with open("serial_config.toml", "r") as f:
            doc = tomlkit.load(f)
            default_port = doc[config_name]["com_port"]
            baud_rate = doc[config_name]["baud_rate"]

        print(f"port: {default_port}")
        print(f"baud rate: {baud_rate}")

        print(free_ports)
        # default port available
        if free_ports.get(default_port, False):
            print("default port is free")
            ser = serial.Serial(default_port, baud_rate)
            device.set_port(ser)

            if device.check_right_port():
                return True

        # look for other port
        for other_port in free_ports:
            # port is available
            if other_port != default_port and free_ports[other_port]:
                ser = serial.Serial(default_port, baud_rate)
                device.set_port(ser)

                if device.check_right_port():
                    return True

        # device isn't connected
        return False

    def make_measurements(self) -> None:
        # self.make_arduino_measurement()
        # self.make_vantage_measurement()
        for device_name, device in self.active_devices.items():
            measruement = device.measure_all()

            with self.last_measurements_lock:
                self.last_measurements[device_name] = measruement

            print(f"Made {device_name} measurement:")
            print(measruement)

    def save_measurements(self):
        if self.saving is not None:
            with self.last_measurements_lock:
                for device_name, save_function in self.saving.items():
                    measurement = self.last_measurements.get(device_name)

                    if measurement is not None:
                        save_function(measurement)

    # def make_arduino_measurement(self) -> None:
    #     with self._arduino_in_lock:
    #         measurement = self._inside_arduino.measure_all()

    #     print("Made inside arduino measurement:")
    #     print(measurement)

    #     if measurement is not None:
    #         with self._arduino_in_measurement_lock:
    #             self._arduino_in_last_measurement = measurement
    #             print("Updated inside arduino measurement")

    # def make_vantage_measurement(self) -> None:
    #     with self._davis_vantage_lock:
    #         measurement = self._davis_vantage.measure_all()

    #     print("Made davis measurement:")
    #     print(measurement)

    #     if measurement is not None:
    #         with self._vantage_measurement_lock:
    #             self._vantage_last_measurement = measurement
    #             print("Updated davis measurement")

    # def get_vantage_last_measurement(self):
    #     with self._vantage_measurement_lock:
    #         return self._vantage_last_measurement

    # def get_arduino_in_last_measurement(self):
    #     with self._arduino_in_lock:
    #         return self._arduino_in_last_measurement

    def list_active_devices(self):
        return list(self.active_devices.keys())


    def get_last_measurement(self, device: DeviceName):
        with self.last_measurements_lock:
            return self.last_measurements.get(device)

    def get_all_measurement(self) -> Dict[DeviceName, WeatherMeasurement]:
        return {DeviceName.ARDUINO_IN: self._arduino_in_last_measurement,
                DeviceName.DAVIS_VANTAGE: self._vantage_last_measurement}


def save_vantage_measurement(measurement):
    db_manager.write_vantage_measurement(measurement)
    


def save_arduino_in_measurement(measurement):
    db_manager.write_arduino_in_measurement(measurement)
    


weatherMonitor = WeatherMonitor([DeviceName.DAVIS_VANTAGE, DeviceName.ARDUINO_IN] ,
                                {DeviceName.DAVIS_VANTAGE: save_vantage_measurement,
                                 DeviceName.ARDUINO_IN: save_arduino_in_measurement})


def monitor_weather():
    print("MONITORING WEATHER")
    while True:
        weatherMonitor.make_measurements()
        weatherMonitor.save_measurements()

        # save_vantage_measurement(weatherMonitor.get_vantage_last_measurement())
        # save_arduino_in_measurement(weatherMonitor.get_arduino_in_last_measurement())
        time.sleep(30)


# @app.on_event("startup")
# async def startup():
db_manager.connect()
db_manager.open_session()


# @app.on_event("shutdown")
# async def shutdown():
# db_manager.close_session()
# db_manager.disconnect()


thread = threading.Thread(target=monitor_weather)
thread.start()
