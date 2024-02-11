import logging
import os

from init_log import config_logging
# config_logging(logging.DEBUG if os.getenv('DEBUG') else logging.WARNING)

import argparse
from typing import Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from vantage_pro2 import VantagePro2
from internal import Internal
from inside_arduino import InsideArduino
from outside_arduino import OutsideArduino
from cyclope import Cyclope
from tessw import TessW

from config.config import make_cfg, Config
from utils import ExtendedJSONResponse, SafetyResponse
from init_log import config_logging
from db_access import make_db_manager
from enum import Enum


cfg: Config = make_cfg()
db_manager = make_db_manager()
stations: Dict[str, Any] = {}


name_to_class = {
    'internal': Internal,
    'davis': VantagePro2,
    'inside-arduino': InsideArduino,
    'outside-arduino': OutsideArduino,
    'cyclope': Cyclope,
    'tessw': TessW,
}


# logger: logging.Logger = logging.getLogger('main')
# init_log(logger)

ProjectName = Enum('ProjectName', {proj: proj for proj in cfg.projects})
StationName = Enum('StationName', {s: s for s in cfg.enabled_stations})


def make_stations():

    for name in cfg.enabled_stations:
        constructor = name_to_class[name]
        station = constructor(name=name)

        for project in ['default'] + cfg.projects:
            # link the configured sensors to the station
            for sensor in cfg.sensors[project]:
                if sensor.settings.station == name:
                    station.sensors.append(sensor)

        # logger.debug(f"adding station '{name}'")
        stations[name] = station
        stations[name].start()


@asynccontextmanager
async def lifespan(_):
    db_manager.connect()
    db_manager.open_session()
    make_stations()
    yield
    db_manager.close_session()
    db_manager.disconnect()

app = FastAPI(lifespan=lifespan, title="Safety at WAO (the Weizmann Astrophysical Observatory)")


@app.get("/config", tags=["info"])
async def show_configuration():
    return cfg


@app.get("/stations", tags=["info"])
async def list_stations():
    return {
        'known': list(cfg.toml['stations'].keys()),
        'enabled': cfg.enabled_stations,
        'in-use': cfg.stations_in_use,
    }


@app.get("/stations/{station}", tags=["info"], response_class=ExtendedJSONResponse)
async def get_station_details(station: StationName):
    name = str(station).replace('StationName.', '')
    if name not in stations:
        return JSONResponse({'msg': f"Bad station name '{name}'  Known stations: {list(stations.keys())}"})

    s = stations[name]
    response = {
        'name': s.name,
        'settings': cfg.station_settings[name],
        'readings': s.readings
    }
    return response


@app.get("/{project}/sensors", tags=["info"], response_class=ExtendedJSONResponse)
async def get_sensors_for_specific_project(project: ProjectName):
    name = str(project).replace('ProjectName.', '')
    return {
        'project': name,
        'sensors': [sensor for sensor in cfg.sensors[name]],
    }


@app.get("/{project}/is_safe", tags=["safety"], response_class=ExtendedJSONResponse)
async def get_project_specific_status(project: ProjectName):
    name = str(project).replace('ProjectName.', '')
    return is_safe(name)


@app.get("/is_safe", tags=["safety"], response_class=ExtendedJSONResponse)
async def get_global_status():
    return is_safe('default')


@app.get("/human-intervention/create", tags=["human-intervention"])
async def create_human_intervention(reason: str):
    internal: Internal = stations['internal']

    internal.human_intervention.create(reason)
    return "ok"


@app.get("/human-intervention/remove", tags=["human-intervention"])
async def remove_human_intervention():
    internal: Internal = stations['internal']

    internal.human_intervention.remove()
    return "ok"


def is_safe(project: str) -> SafetyResponse:
    if project is None:
        project = 'default'

    for station in stations:
        if hasattr(station, 'calculate_sensors'):
            station.calculate_sensors()

    ret = SafetyResponse()
    for sensor in cfg.sensors[project]:
        if not sensor.safe:
            ret.safe = False
            for reason in sensor.reasons:
                ret.reasons.append(reason)
    return ret


if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser(description="A safety data-gathering daemon")
    parser.add_argument('-d', '--debug', action='store_true', help='Debug to stdout')

    args = parser.parse_args()
    config_logging(logging.DEBUG if args.debug else logging.INFO)

    svr = cfg.server
    uvicorn.run("main:app", host=svr.host, port=svr.port, reload=True)
