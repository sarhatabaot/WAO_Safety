from fastapi import FastAPI, APIRouter
from enum import Enum

from VantagePro2 import VantagePro2

vantagePro = VantagePro2()

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
    return {"temperature": vantagePro.get_measurement().temperature_in,
            "measurement_time": vantagePro.last_measurement_time,
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
