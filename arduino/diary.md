+ On ubuntu use `snap install` to get arduino, not `apt install`, `synaptic`, etc. - the version available to apt
is extremely old (1.0.5), and many libraries have to be installed manually in complicate ways or don't install correctly.
The snap version is up to date (1.8.13)

+ side effect of using the snap is that the files by default end up in an user directory like `~/snap/arduino/41`
and not in a system directory. I'd be more used to a personal sketchbook directory not buried in `~/snap/` and in a systemwise installation, whatever. The location of the personal sketchbook directory can be changed in the preferences though. Be careful not to duplicate libraries both under `~/snap/arduino/current/Arduino/libraries/` and in the default `sketchbook` location.

+ jumpered the BMI088 to use address `0x18` for the accelerometer and avoid conflict with the LIS3D. To connect, `BMI088_ACC_ADDRESS` has to be modified in `BMI088.h` (REMEMBER IN FUTURE INSTALLATIONS). Strangely I2Cscanner still doesn't see the BMI088 on address `0x18` if also the LIS3D is connected, but the BMI088_example works, as well as further programs of mine for reading both.

+ reading the TempAndHumidity sensor involves a delay of >500ms which is in the library code. This is a dead time during which other sensors cannot be scanned for potential trigger events, unless the internal programming is changed.
I doubt this can be done, or things can be improved using interrupt programming.

+ there seems to be a diaphony between digital lines. In the present configuration, if the functions reading the gyroscope, the light sensor and the state of the piezo sensor flag are called one immediately after the other and in that sequence, the piezo reports 1. Moving the piezo from pin D4 to D7 didn't help, a delay of 100ms after the first function does.