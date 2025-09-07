# LAST_MountArduinoSensors

Arduino sensors for a tentative instrumentation of LAST mounts.

This project (Arduino sketch + Matlab class) was tried on a Seeeduino Lotus v1.1, because
of the convenient multiple Grove connectors.


## Provisional sensor set:

| ***Monitored quantity***| ***device***         | ***pin/address***| ***required library***|
|-------------------------|----------------------|------------------|----------------------:|
| **temperature**         | *Grove temperature*  | A0               |    --                 |
| **temperature**         | *Grove temperature*  | A2               |    --                 |
| **rain**                | *Grove water*        | D2               |    --                 |
| **temperature**         | *Grove Temp/humidity*| D3, protocol     |  DHT                  |
| **humidity**            | *Grove Temp/humidity*|   "  "           |   " "                 |
| **shock**               | *Grove Piezo vibr.*  | D4               |   --                  |
| **light visible/IR**    | *Grove dig. light*   | *I2C 0x29*       | Digital_Light_TSL2561 |
| **acceleration**        | BMI088               | *I2C 0x18*       |  BMI088               |
| **gyroscope**           | BMI088               | *I2C 0x18*       |  " "                  |
| **temperature**         | BMI088               | *I2C 0x18*       |  " "                  |
| **acceleration**        | LSI3DHTR             | *I2C 0x19*       |  LSI3DHTR             |
| **temperature**         | LSI3DHTR             | *I2C 0x19*       |  " "                  |


The sketch associated to this set was `Mount_multiQuery.ino`.

### libraries to install in Arduino with the library manager:

Besides the hardware ones,

- **Statistic** by Rob Tilaart,
- **SimpleSerialShell**