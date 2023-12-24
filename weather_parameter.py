from enum import Enum


class WeatherParameter(str, Enum):
    TEMPERATURE_IN = "temperature_in",
    TEMPERATURE_OUT = "temperature_out",

    HUMIDITY_IN = "humidity_in",
    HUMIDITY_OUT = "humidity_out",

    PRESSURE_IN = "pressure_in",
    PRESSURE_OUT = "pressure_out",

    WIND_SPEED = "wind_speed",
    WIND_DIRECTION = "wind_direction",

    VISIBLE_LUX_IN = "visible_lux_in",
    VISIBLE_LUX_OUT = "visible_lux_out",

    IR_LUMINOSITY = "ir_luminosity",

    RAIN = "rain",
    SOLAR_RADIATION = "solar_radiation",

    PRESENCE = "presence",
    FLAME = "flame",
    CO2 = "co2",
    VOC = "voc",
    RAW_H2 = "raw_h2",
    RAW_ETHANOL = "raw_ethanol",

    DEW_POINT = "dew_point"
