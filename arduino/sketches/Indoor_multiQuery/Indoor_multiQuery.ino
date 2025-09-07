/////////// used libraries and card definitions: ///////////////////

#include <SimpleSerialShell.h>


#define LIGHTPIN 0  // photoresistor to 5V, with 10Kohm pulldown

#define FLAMEPIN 1  // analog IR flame detector

#define PIR_MOTION_SENSOR 2  // digital presence detector

#define NAN "NaN"
#define CONNECTED F("connected")
#define UNCONNECTED F("didn't connect")
#define SPC F(" ") // feels a little idiot

// SGP30 air quality sensor
#include "SparkFun_SGP30_Arduino_Library.h" // Click here to get the library: http://librarymanager/All#SparkFun_SGP30
#include <Wire.h>
SGP30 airQualitySensor;

//High Precision Barometric Pressure Sensor DPS310
#include <Dps310.h>
Dps310 Dps310PressureSensor = Dps310();
//Dps310PressureSensor.begin(Wire, 0x76); //if jumpered


///////////////// functions which implement each command ////////////////

int script_id(int argc, char **argv){
  shell.println(F("Running " __FILE__ ", Built " __DATE__));
}


int what_connected(int argc, char **argv){
  shell.println("photoresistor - can't really say");
  shell.println("flame phototransistor - can't really say");
  shell.println("PIR sensor - can't really say");
  shell.println("high precision barometer/temperature sensor - can't really say");
  if (airQualitySensor.getSerialID()==SGP30_SUCCESS) {
        shell.println(F("SGP30 CO2/TVOC sensor"));
  }
}


int read_light(int argc, char **argv){
  float pulldown=10000;
  int A=analogRead(LIGHTPIN);
  float resistance=(float)(1023-A)*pulldown/A; //get the resistance of the sensor;
  // conversion to putative Lux based on looking up the datasheet
  float lux=(float) pow(2.0535*resistance/25000,-3.2);
  shell.print(F("light (Lux): ")); shell.println(lux,3);
}


int read_flame(int argc, char **argv){
// using gravity "flame" sensor https://wiki.dfrobot.com/Flame_sensor_SKU__DFR0076
// spec range is actually 20cm (4.8V) ~ 100cm (1V)
// https://raw.githubusercontent.com/Arduinolibrary/Source/master/YG1006ataSheet.pdf
  int A=analogRead(FLAMEPIN);
  shell.print(F("IR reading: ")); shell.println(A);
}


int read_presence(int argc, char **argv){
// using the Grove PIR sensor, nominal (adjustable) range 0.1 - 6m, angle 120°
// https://wiki.seeedstudio.com/Grove-PIR_Motion_Sensor/
  shell.print(F("Presence: ")); shell.println(digitalRead(PIR_MOTION_SENSOR));
}


int read_temperature(int argc, char **argv){
  //unsigned long t1=millis();
  uint8_t oversampling = 5;
  int16_t ret;
  float temperature;
  ret = Dps310PressureSensor.measureTempOnce(temperature, oversampling);
  //shell.print(F("   printed in ")); shell.print(millis()-t1); shell.println(F("ms"));
  if (ret !=0) {
      shell.print(F("Temperature: ")); shell.print(NAN); shell.println(F("°C"));
  }
  else {
      shell.print(F("Temperature: ")); shell.print(temperature,2); shell.println(F("°C"));
  }
}


int read_pressure(int argc, char **argv){
  //unsigned long t1=millis();
  uint8_t oversampling = 5;
  int16_t ret;
  float pressure;
  ret = Dps310PressureSensor.measurePressureOnce(pressure, oversampling);
  //shell.print(F("   printed in ")); shell.print(millis()-t1); shell.println(F("ms"));
  if (ret !=0) {
      shell.print(F("Pressure: ")); shell.print(NAN); shell.println(F("hPa"));
  }
  else {
      shell.print(F("Pressure: ")); shell.print(pressure/100,3); shell.println(F("hPa"));
  }
}


int read_co2_tvoc_h2_ethanol(int argc, char **argv){
    // (for the first few seconds the measurements are bogus)
    //measure CO2 and TVOC levels
    airQualitySensor.measureAirQuality();
    shell.print("CO2: ");
    shell.print(airQualitySensor.CO2);
    shell.print(" ppm\tTVOC: ");
    shell.print(airQualitySensor.TVOC);
    shell.print(" ppb\tRaw H2: ");
    //get raw values for H2 and Ethanol
    airQualitySensor.measureRawSignals();
    shell.print(airQualitySensor.H2);
    shell.print(" \tRaw Ethanol: ");
    shell.println(airQualitySensor.ethanol);
}

//////////////// Setup and Loop ///////////////////////

void setup()
{
  Wire.begin();
  Serial.begin(115200);
  while (!Serial)
  {
  };

  // define the commands implemented
  shell.attach(Serial);
  shell.addCommand(F("id?"),script_id);
  shell.addCommand(F("what?"),what_connected);
  shell.addCommand(F("light?"),read_light);
  shell.addCommand(F("flame?"),read_flame);
  shell.addCommand(F("presence?"),read_presence);
  shell.addCommand(F("pressure?"),read_pressure);
  shell.addCommand(F("temp?"),read_temperature);
  shell.addCommand(F("gas?"),read_co2_tvoc_h2_ethanol);

  // define mode of digital i/o
  pinMode(PIR_MOTION_SENSOR, INPUT);

  Dps310PressureSensor.begin(Wire);

  // setup and initialize various digital sensors
  // air quality sensor SGP30
  if (airQualitySensor.begin() == false) {
    Serial.println("No SGP30 Detected. Check connections.");
  }
  //Initializes sensor for air quality readings
  //measureAirQuality should be called in one second increments after a call to initAirQuality
  airQualitySensor.initAirQuality();
}


void loop()
{  
  //characters are processed one at a time I think, this has to be executed as often as possible
  shell.executeIfInput();
}
