from typing import List
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from fastapi.responses import JSONResponse

from db_access import DbManager

from vantage_pro2 import VantagePro2
from calculator import Calculator
from inside_arduino import InsideArduino
from outside_arduino import OutsideArduino
from station import Station

from utils import cfg, SingletonFactory

db_manager = SingletonFactory.get_instance(DbManager)

name_to_class = {
    'calculator': Calculator,
    'davis': VantagePro2,
    'inside-arduino': InsideArduino,
    'outside-arduino': OutsideArduino,
}
stations: List[Station] = list()


def make_stations():
    for name in cfg.enabled_stations:
        station = name_to_class[name](name=name)
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


@app.get("/stations/{station}")
async def get_station(station_name: str):
    s = [s for s in stations if s.name == station_name]
    response = {
        'name': s.name,
        'readings': []
    }
    return JSONResponse(response)

# weather_router = APIRouter(prefix="/weather")
# safety_router = APIRouter(prefix="/safety_config")
#
# app.include_router(weather_router)
# app.include_router(safety_router)
#
# control_router = APIRouter(prefix="/control")


if __name__ == "__main__":
    import uvicorn

    config = cfg.get('server')
    uvicorn.run("main:app", host=config['host'], port=config['port'], reload=True)
