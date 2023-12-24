import time
import threading
from enum import Enum
from typing import Optional

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

app = FastAPI()

com_ports = serial.tools.list_ports.comports()
assigned_ports = {com_port.name: False for com_port in com_ports}


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


weatherRouter = APIRouter(prefix="/weather")


@weatherRouter.get("/temperature_in")
async def get_temperature_in():
    return {"temperature": weatherMonitor.get_vantage_last_measurement().get_parameter(WeatherParameter.TEMPERATURE_IN),
            "measurement_time": weatherMonitor.get_vantage_last_measurement().timestamp,
            "source": "vantage pro"}


class Project(str, Enum):
    Last = "last"
    Mast = "mast"


safetyRouter = APIRouter(prefix="/safety")


@safetyRouter.get("/{project}")
async def get_safety(project: Project):
    return {"is_safe": True}


app.include_router(weatherRouter)
app.include_router(safetyRouter)


class WeatherMonitor:
    def __init__(self):
        # self._devices
        self._vantage_last_measurement: Optional[WeatherMeasurement] = None
        self._vantage_measurement_lock = threading.Lock()

        self._arduino_in_last_measurement: Optional[WeatherMeasurement] = None
        self._arduino_in_measurement_lock = threading.Lock()

        self._davis_vantage_lock = threading.Lock()
        self._arduino_in_lock = threading.Lock()

        self._davis_vantage = VantagePro2()
        if not self._connect_device(self._davis_vantage, "VantagePro2"):
            self._davis_vantage = None

        self._inside_arduino = InsideArduino()
        if not self._connect_device(self._inside_arduino, "InsideArduino"):
            self._inside_arduino = None

        self._outside_arduino = OutsideArduino()

    def _connect_device(self, device: SerialWeatherDevice, config_name: str) -> bool:
        with open("serial_config.toml", "r") as f:
            doc = tomlkit.load(f)
            default_port = doc[config_name]["com_port"]
            baud_rate = doc[config_name]["baud_rate"]

        # default port available
        if assigned_ports.get(default_port, False):
            ser = serial.Serial(default_port, baud_rate)
            device.set_port(ser)

            if device.check_right_port():
                return True

        # look for other port
        for other_port in assigned_ports:
            # port is available
            if other_port != default_port and assigned_ports[other_port]:
                ser = serial.Serial(default_port, baud_rate)
                device.set_port(ser)

                if device.check_right_port():
                    return True

        # device isn't connected
        return False

    def make_measurements(self) -> None:
        self.make_arduino_measurement()
        self.make_vantage_measurement()

    def make_arduino_measurement(self) -> None:
        with self._arduino_in_lock:
            measurement = self._inside_arduino.measure()

        print("Made inside arduino measurement:")
        print(measurement)

        if measurement is not None:
            with self._arduino_in_measurement_lock:
                self._arduino_in_last_measurement = measurement
                print("Updated inside arduino measurement")

    def make_vantage_measurement(self) -> None:
        with self._davis_vantage_lock:
            measurement = self._davis_vantage.measure()

        print("Made davis measurement:")
        print(measurement)

        if measurement is not None:
            with self._vantage_measurement_lock:
                self._vantage_last_measurement = measurement
                print("Updated davis measurement")

    def get_vantage_last_measurement(self):
        with self._vantage_measurement_lock:
            return self._vantage_last_measurement

    def get_arduino_in_last_measurement(self):
        with self._arduino_in_lock:
            return self._arduino_in_last_measurement


weatherMonitor = WeatherMonitor()


def monitor_weather():
    print("MONITORING WEATHER")
    while True:
        weatherMonitor.make_measurements()

        save_vantage_measurement(weatherMonitor.get_vantage_last_measurement())
        save_arduino_in_measurement(weatherMonitor.get_arduino_in_last_measurement())
        time.sleep(30)


def save_vantage_measurement(measurement):
    # db_manager.write_vantage_measurement(measurement)
    pass


def save_arduino_in_measurement(measurement):
    # db_manager.write_arduino_in_measurement(measurement)
    pass


# @app.on_event("startup")
# async def startup():
# db_manager.connect()
# db_manager.open_session()


# @app.on_event("shutdown")
# async def shutdown():
# db_manager.close_session()
# db_manager.disconnect()


thread = threading.Thread(target=monitor_weather)
thread.start()
