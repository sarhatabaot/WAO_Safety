<h1>Explanation about config files</h1>
In general, enum names are used for file names and table names in the config files.

<h2>Device Config File</h2>
Config files about the devices are in the folder "device_config".
The file "active_devices.toml" has a table with the name of a member of DeviceName enum.
The only value in the table is a boolean "active" that is True or False

The file "calculation_config.toml" has parameters about calculation devices.
The format is: </br>

[<device_name>]</br>
params = {key_1 = value_1, key_2 = value_2, ...}

The file "serial_config.toml" has parameters about serial devices.
The format is:</br>

[<device_name>]</br>
com_port = string value
baud_rate = int value

<h2>Weather Safety Config Files</h2>
Config files about weather safety are in the folder "safety_config".
Default configuration are found in "default.toml". The format is:</br>

[parameter_name]</br>
min = min value</br>
max = max value</br>
source = string, device name</br>
interval = measuring interval in seconds</br>
total_time = total time to check in safe zone</br>

In the "default.toml" file all field should be filled.

If we need different configurations for some project, the files "last.toml" and "mast.toml". 
If there are no default configurations for a parameter, the file has to specify all other fields.
if there is a default configuration for a parameter, then only speific values can be changed. 