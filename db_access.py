from typing import Optional

from sqlalchemy import create_engine, MetaData, Engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session

from config.config import cfg, DatabaseConfig
from vantage_pro2 import VantageProReading, VantageProDatum
from inside_arduino import InsideArduinoReading, InsideArduinoDatum
from outside_arduino import OutsideArduinoReading, OutsideArduinoDatum


Base = None
DavisDbClass = None
ArduinoInDbClass = None
ArduinoOutDbClass = None


class DbManager:
    def __init__(self):
        conf = cfg.database
        self.schema = conf.schema
        self.db_url = f"postgresql+psycopg2://{conf.user}:{conf.password}@{conf.host}/{conf.name}"

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

    def __del__(self):
        self.close_session()
        self.disconnect()

    def write_vantage_measurement(self, reading: VantageProReading):
        davis = DavisDbClass(
            temp_in = reading.datums[VantageProDatum.InsideTemperature],
            humidity_in = reading.datums[VantageProDatum.InsideHumidity],
            pressure_out = reading.datums[VantageProDatum.Barometer],
            temp_out = reading.datums[VantageProDatum.OutsideTemperature],
            humidity_out = reading.datums[VantageProDatum.OutSideHumidity],
            wind_speed = reading.datums[VantageProDatum.WindSpeed],
            wind_direction = reading.datums[VantageProDatum.WindDirection],
            rain = reading.datums[VantageProDatum.RainRate],
            solar_radiation = reading.datums[VantageProDatum.SolarRadiation],
            tstamp = reading.tstamp,
        )

        self.session.add(davis)
        self.session.commit()

    def write_arduino_in_measurement(self, reading: InsideArduinoReading):
        arduino_in = ArduinoInDbClass(
            presence = reading.datums[InsideArduinoDatum.Presence],
            temp_in = reading.datums[InsideArduinoDatum.TemperatureIn],
            pressure_in = reading.datums[InsideArduinoDatum.PressureIn],
            visible_lux_in = reading.datums[InsideArduinoDatum.VisibleLuxIn],
            flame = reading.datums[InsideArduinoDatum.Flame],
            co2 = reading.datums[InsideArduinoDatum.CO2],
            voc = reading.datums[InsideArduinoDatum.VOC],
            raw_h2 = reading.datums[InsideArduinoDatum.RawH2],
            raw_ethanol = reading.datums[InsideArduinoDatum.RawEthanol],
            tstamp = reading.tstamp,
        )

        self.session.add(arduino_in)
        self.session.commit()

    def write_arduino_out_measurement(self, reading: OutsideArduinoReading):
        arduino_out = ArduinoOutDbClass(
            temp_out = reading.datum[OutsideArduinoDatum.TemperatureOut],
            humidity_out = reading.datum[OutsideArduinoDatum.HumidityOut],
            pressure_out = reading.datum[OutsideArduinoDatum.PressureOut],
            dew_point  = reading.datum[OutsideArduinoDatum.DewPoint],
            visible_lux_out = reading.datum[OutsideArduinoDatum.VISIBLE_LUX_OUT],
            ir_luminosity = reading.datum[OutsideArduinoDatum.IrLuminosity],
            wind_speed = reading.datum[OutsideArduinoDatum.WindSpeed],
            wind_direction = reading.datum[OutsideArduinoDatum.WindDirection],
            tstamp = reading.tstamp
        )

        self.session.add(arduino_out)
        self.session.commit()
