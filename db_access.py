from typing import Optional

from sqlalchemy import create_engine, MetaData, Engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
import tomlkit

from weather_measurement import WeatherMeasurement
from weather_parameter import WeatherParameter

CONFIG_PATH = "/home/ocs/python/security/WeatherSafety/db_config.toml"


def get_db_url() -> str:
    with open(CONFIG_PATH, "r") as config_fp:
        config_doc = tomlkit.load(config_fp)

        db_host = config_doc["database"]["host"]

        db_user = config_doc["database"]["user"]
        db_password = config_doc["database"]["password"]

        db_name = config_doc["database"]["name"]

        return f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}/{db_name}"


def get_db_schema() -> str:
    with open(CONFIG_PATH, "r") as config_fp:
        config_doc = tomlkit.load(config_fp)

        return config_doc["database"]["schema"]


Base = None
DavisDbClass = None
ArduinoInDbClass = None
ArduinoOutDbClass = None


class DbManager:
    def __init__(self):
        self.schema = get_db_schema()
        self.db_url = get_db_url()

        self.vantage_table_name = ""
        self.arduino_in_table_name = ""

        self.session: Optional[Session] = None
        self.metadata: Optional[MetaData] = None
        self.engine: Optional[Engine] = None

        self.ArduinoIn = None
        self.Vantage = None
        self.Base = None

    def connect(self):
        global Base, DavisDbClass, ArduinoInDbClass, ArduinoOutDbClass

        self.engine = create_engine(self.db_url)

        Base = automap_base()
        Base.prepare(autoload_with=self.engine, schema=self.schema)

        DavisDbClass = Base.classes.davis
        ArduinoInDbClass = Base.classes.arduino_in
        ArduinoOutDbClass = Base.classes.arduino_out

    def disconnect(self):
        self.engine.dispose()

    def open_session(self):
        self.session = Session(self.engine)

    def close_session(self):
        self.session.close()

    def write_vantage_measurement(self, measurement: WeatherMeasurement):
        davis = DavisDbClass(
            temp_in=measurement.get_parameter(WeatherParameter.TEMPERATURE_IN),
            humidity_in=measurement.get_parameter(WeatherParameter.HUMIDITY_IN),
            pressure_out=measurement.get_parameter(WeatherParameter.PRESSURE_OUT),
            temp_out=measurement.get_parameter(WeatherParameter.TEMPERATURE_OUT),
            humidity_out=measurement.get_parameter(WeatherParameter.HUMIDITY_OUT),
            wind_speed=measurement.get_parameter(WeatherParameter.WIND_SPEED),
            wind_direction=measurement.get_parameter(WeatherParameter.WIND_DIRECTION),
            rain=measurement.get_parameter(WeatherParameter.RAIN),
            solar_radiation=measurement.get_parameter(WeatherParameter.SOLAR_RADIATION),
            tstamp=measurement.get_timestamp(),
        )

        self.session.add(davis)
        self.session.commit()

    def write_arduino_in_measurement(self, measurement: WeatherMeasurement):
        arduino_in = ArduinoInDbClass(
            presence=measurement.get_parameter(WeatherParameter.PRESENCE),
            temp_in=measurement.get_parameter(WeatherParameter.TEMPERATURE_IN),
            pressure_in=measurement.get_parameter(WeatherParameter.PRESSURE_IN),
            visible_lux_in=measurement.get_parameter(WeatherParameter.VISIBLE_LUX_IN),
            flame=measurement.get_parameter(WeatherParameter.FLAME),
            co2=measurement.get_parameter(WeatherParameter.CO2),
            voc=measurement.get_parameter(WeatherParameter.VOC),
            raw_h2=measurement.get_parameter(WeatherParameter.RAW_H2),
            raw_ethanol=measurement.get_parameter(WeatherParameter.RAW_ETHANOL),
            tstamp=measurement.get_timestamp()
        )

        self.session.add(arduino_in)
        self.session.commit()

    def write_arduino_out_measurement(self, measurement: WeatherMeasurement):
        arduino_out = ArduinoOutDbClass(
            temp_out=measurement.get_parameter(WeatherParameter.TEMPERATURE_OUT),
            humidity_out=measurement.get_parameter(WeatherParameter.HUMIDITY_OUT),
            pressure_out=measurement.get_parameter(WeatherParameter.PRESSURE_OUT),
            dew_point=measurement.get_parameter(WeatherParameter.DEW_POINT),
            visible_lux_out=measurement.get_parameter(WeatherParameter.VISIBLE_LUX_OUT),
            ir_luminosity=measurement.get_parameter(WeatherParameter.IR_LUMINOSITY),
            wind_speed=measurement.get_parameter(WeatherParameter.WIND_SPEED),
            wind_direction=measurement.get_parameter(WeatherParameter.WIND_DIRECTION),
            tstamp=measurement.get_timestamp()
        )

        self.session.add(arduino_out)
        self.session.commit()
