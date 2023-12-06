from typing import Optional

import sqlalchemy
from sqlalchemy import create_engine, MetaData, Engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
import tomlkit

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
        self.engine = create_engine(self.db_url)
        print("engine")
        self.metadata = MetaData()
        print(self.metadata.tables)
        print(self.schema)

        self.metadata.reflect(self.engine, schema=self.schema,
                              only=["arduino_in", "davis"])

        self.Base = automap_base(metadata=self.metadata)

        for table in self.metadata.tables:
            print(table)

        self.Base.prepare()

        print(dir(self.Base.classes))
        self.ArduinoIn = self.Base.classes.arduino_in
        self.Vantage = self.Base.classes.davis

        self.session = None

    def disconnect(self):
        self.engine.dispose()

    def open_session(self):
        self.session = Session(self.engine)

    def close_session(self):
        self.session.close()

    def _convert_to_vantage_db_type(self, measurement):
        return self.Vantage()

    def _convert_to_vantage_type(self, measurement):
        pass

    def _convert_to_arduino_in_db_type(self, measurement):
        return self.ArduinoIn()

    def _convert_to_arduino_in_type(self, measurement):
        pass

    def write_vantage_measurement(self, measurement):
        # self.session.add(self._convert_to_vantage_db_type(measurement))
        # self.session.flush()
        pass

    def write_arduino_in_measurement(self, measurement):
        # self.session.add(self._convert_to_arduino_in_db_type(measurement))
        # self.session.flush()
        pass
