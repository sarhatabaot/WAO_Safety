import datetime
import logging
from typing import List, Dict
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, Query
from fastapi.responses import JSONResponse
from datetime import timedelta as td

from db_access import DbManager

from vantage_pro2 import VantagePro2
from internal import Internal
from inside_arduino import InsideArduino
from outside_arduino import OutsideArduino
from station import Station, Sensor, SafetyResponse

from config.config import cfg
from utils import SingletonFactory, ExtendedJSONResponse, Never
from init_log import init_log

# db_manager = SingletonFactory.get_instance(DbManager)
db_manager = SingletonFactory(DbManager)

name_to_class = {
    'internal': Internal,
    'davis': VantagePro2,
    'inside-arduino': InsideArduino,
    'outside-arduino': OutsideArduino,
}
stations: List[Station] = list()

logger: logging.Logger = logging.getLogger('main')
init_log(logger)


def make_stations():
    for name in cfg.stations_in_use:
        constructor = name_to_class[name]
        station = constructor(name=name)
        logger.info(f"adding station '{station.name}'")
        stations.append(station)
        station.start()


@asynccontextmanager
async def lifespan(app):
    # db_manager.connect()
    # db_manager.open_session()
    make_stations()
    yield
    db_manager.close_session()
    db_manager.disconnect()

app = FastAPI(lifespan=lifespan)


# @app.get("/")
# async def root():
#     return {"message": "Hello World"}


@app.get("/stations/list")
async def list_stations():
    return JSONResponse([station.name for station in stations])


@app.get("/stations/{station}", response_class=ExtendedJSONResponse)
async def get_station(station: str):
    s = [s for s in stations if s.name == station]
    response = {
        'name': s[0].name,
        'readings': s[0].readings
    }
    return response


@app.get("/{project}/is_safe", response_class=ExtendedJSONResponse)
async def get_is_safe(project: str):
    return is_safe(project)


@app.get("/is_safe", response_class=ExtendedJSONResponse)
async def get_is_safe():
    return is_safe()

# weather_router = APIRouter(prefix="/weather")
# safety_router = APIRouter(prefix="/safety_config")
#
# app.include_router(weather_router)
# app.include_router(safety_router)
#
# control_router = APIRouter(prefix="/control")


def is_safe(project: str = None) -> SafetyResponse:
    # walk the enabled stations
    ret = SafetyResponse()  # global, for all sensors
    for station in stations:
        # and the respective enabled sensors
        for sensor in station.sensors:
            if sensor.became_safe is not Never:
                now = datetime.datetime.now()
                if not sensor.has_settled():
                    ret.safe = False
                    td_left = (sensor.became_safe + td(seconds=sensor.settings.settling)) - now
                    ret.reasons.append(f"sensor '{sensor.name}' needs {td_left} seconds to settle")

            if not sensor.safe:
                ret.safe = False
                for reason in sensor.reasons:
                    ret.reasons.append(reason)
    return ret


if __name__ == "__main__":
    import uvicorn

    config = cfg.get('server')
    uvicorn.run("main:app", host=config['host'], port=config['port'], reload=True)
