import time
import threading
from enum import Enum
from typing import Optional

from fastapi import FastAPI, APIRouter

from VantagePro2 import VantagePro2, VantageProMeasurement
from InsideArduino import InsideArduino, InsideArduinoMeasurement
from db_access import DbManager

# db_manager = DbManager()

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


weatherRouter = APIRouter(prefix="/weather")


@weatherRouter.get("/temperature_in")
async def get_temperature_in():
    return {"temperature": weatherMonitor.get_vantage_last_measurement().temperature_in,
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
        self._vantage_last_measurement: Optional[VantageProMeasurement] = None
        self._vantage_measurement_lock = threading.Lock()

        self._arduino_in_last_measurement: Optional[InsideArduinoMeasurement] = None
        self._arduino_in_measurement_lock = threading.Lock()

        self._davis_vantage_lock = threading.Lock()
        self._arduino_in_lock = threading.Lock()

        self._davis_vantage = VantagePro2()
        self._inside_arduino = InsideArduino()

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
