# LAST_EnvironmentArduinoSensors

Arduino sensors for LAST enclosure monitoring: meteo, presence, dust, smoke, fire, etc.

This project (Arduino sketch + Matlab class) is being tried on a Seeeduino Cortex-M0+

## Provisional sensor set:

| ***Monitored quantity***| ***device***      | ***pin/address***| ***required library***    |
|-------------------------|-------------------|------------------|--------------------------:|
| **Wind direction**      | Inspeed e-vane    | A0               |    --                     |
| **Wind speed**          | Inspeed anemometer| D0               | (TimerTCC0)               |
| **light discrimination**| *Grove dig. light*| I2C 0x29         | Grove Digital Light Sensor|
| **fire detection**      | Gravity flame det.| A1               |   --                      |
| **barometric pressure** | MS8607            | I2C 0x40, 0x76   |  MS8607                   |
| **humidity**            | MS8607            |   "  "           |    "                      |
| **temperature**         | MS8607            |   "  "           |    "                      |
| **dust**                | Grove Dust        | D1               |   --                      |
| **smoke detection**     | SGP30 (VOC & CO2) | I2C 0x58         |  SGP30                    |
| **human presence**      | Grove PIR motion  | D2               |   --                      |

Sketch: `Environment_MultiQuery.ino`

Matlab class: `EnvironmentArduinoSensors.m`

## Second version: outdoor and indoor

### Outdoor

Using the Seeduino Cortex-M0+

| ***Monitored quantity***| ***device***      | ***pin/address***| ***required library***    |
|-------------------------|-------------------|------------------|--------------------------:|
| **Wind direction**      | Inspeed e-vane    | A0               |    --                     |
| **Wind speed**          | Inspeed anemometer| D0               | (TimerTCC0)               |
| **light discrimination**| *Grove dig. light*| I2C 0x29         | Grove Digital Light Sensor|
| **barometric pressure** | MS8607            | I2C 0x40, 0x76   |  MS8607                   |
| **humidity**            | MS8607            |   "  "           |    "                      |
| **temperature**         | MS8607            |   "  "           |    "                      |

#### Electrical connections of the Inspeed sensors:

| Vane:|          |
|------|----------|
| red  | **+3.3V**|
| white| **A0**   |
| black| **GND**  |


| Cups:|                                                  |
|------|--------------------------------------------------|
| red  | **+5V**                                          |
| white| **DI0** pulled up to **+3.3V** with 10kΩ resistor|
| black| **GND**                                          |

Sketch: `Outdoor_multiQuery.ino`

Matlab class: `OutdoorMeteoSensors.m`

### Indoor

Using the Seeduino Lotus v1.1, because of the convenient multiple Grove connectors.

| ***Monitored quantity***| ***device***                  | ***pin/address***    | ***required library***|
|-------------------------|-------------------------------|----------------------|----------------------:|
| **light**               | photoresistance PVD-P8103     | Vcc/A0 pulldown 10kΩ |   --                  |
| **fire detection**      | Gravity flame det.            | A1                   |   --                  |
| **human presence**      | Grove PIR motion              | D2                   |   --                  |
| **barometric pressure** | Grove high precision barometer| I2C 0x77             |  DPS310               |
| **temperature**         | " "                           |   "  "               |    "                  |
| **smoke detection**     | SGP30 (VOC & CO2)             | I2C 0x58             |  SGP30                |
|                         |                               |                      |                       |

Sketch: `Indoor_multiQuery.ino`

Matlab class: `IndoorSensors.m`

Photoresistance calibration: my understanding from the datasheet is that, assuming a nominal
resistance of 25kΩ at 10Lux, and a pulldown resistance of 10kΩ, the conversion formula should be
```
E[lux]=(2.0535*R / 25kΩ)^(-16/5) = (2.0535*(1023-A)*10kΩ/A / 25kΩ)^(-3.2) =
      = (2.0535*(1023-A)/(2.5*A))^(-3.2)
```
Where A is the analog readout (0:1023).

## Additional Arduino libraries required:

- SimpleSerialShell
- SparkFun_PHT_MS8607_Arduino_Library
- Grove Digital Light Sensor

## If compile fails on arduino 1.8.5 snap, check:

The target board should be set to Seeeduino Zero for outdoor and to Seeeduino Lotus for indoor.
To install support for the Seed boards,
[see the instructions](https://wiki.seeedstudio.com/Seeed_Arduino_Boards/)
(installation from the board manager can take a few minutes).

Complaints, when compilation is attempted while the target board is a generic arduino, can be:
"TimerTCC0.h: No such file or directory", and "error: 'D0' was not declared in this scope", or
"board not found on /dev/ttyUSB0", etc
