/////////// used libraries and card definitions: ///////////////////

#include <SimpleSerialShell.h>

/* Anemometer:
 
  Read wind speed and direction from Inspeed cup anemometer and vane.
  
  The e-vane is supplied by the 3.3V line, and provides an analog signal for the range 0-360°.
  Its output is connected to analog0. Nominally this is said to give an analog signal from
  5%*Vs to 95%Vs, i.e. 0.165-3.135V. However, that is seen to cover the full a0 range on the
  Seeeduino cortex M0+ (which should be nominally 0-5V). Supplying it with the board 5V line
  instead, it saturates the a0 input.

  The cup anemometer is connected to digital 0. We have the D3 rotor, which should provide
  1 pulse per turn, and 1 turn/sec per 1.207008m/sec.
  Operationally, I'd expect 0.5 to 100 turns per second, at most. The Hall sensor conducts
  for about 1/4 of the turn, which means that one has to detect a 0 pulse which could last
  from 2.5 to 500ms.
  The measurement is done arming an interrupt on falling transitions of the digital input.
  The interrupt routine updates the time elapsed since its previous call, and the inverse
  period is translated to a frequency.
  If no new pulse was detected for Tmeas, the velocity is resetted to 0.
*/
#include <TimerTCC0.h>

const int AnemometerPin = D0;
const int VanePin = A0;
const float vcal=1207008; // calibration factor, m*us/s
const int Tmeas=2000000; // microsec
volatile unsigned int tprevious; // microsec
volatile float wspeed;

// MS8607 barometer, hygrometer
#include <Wire.h>
#include <SparkFun_PHT_MS8607_Arduino_Library.h>
MS8607 barometricSensor;
bool haveMS8607;

// Grove Digital Light Sensor
#include <Digital_Light_TSL2561.h>

#define NAN "NaN"
#define CONNECTED F("connected")
#define UNCONNECTED F("didn't connect")
#define SPC F(" ") // feels a little idiot

//////////////// Setup and Loop ///////////////////////

void setup() {
  // initialize the anemometer pin as a input:
  pinMode(AnemometerPin, INPUT);
  // interrupt to read deltaT since previous pulse
  attachInterrupt(digitalPinToInterrupt(AnemometerPin),elapsed,FALLING);
  //interrupt to reset deltaT if no new pulse arrived
  TimerTcc0.initialize(Tmeas);
  TimerTcc0.attachInterrupt(resetElapsed);
  
  // shell:
  Serial.begin(115200);
  while (!Serial)
  {
  };

  // MS8607 Barometer,termometer,higrometer
  Wire.begin();
  Wire.setClock(400000); //Communicate at faster 400kHz I2C
  if (!barometricSensor.begin())
    {
      Serial.println("MS8607 sensor did not respond. Please check wiring.");
    }
    else
    {
      //The sensor has 6 resolution levels. The higher the resolution the longer each
      //reading takes to complete.
      //  barometricSensor.set_pressure_resolution(MS8607_pressure_resolution_osr_256); //1ms per reading, 0.11mbar resolution
      //  barometricSensor.set_pressure_resolution(MS8607_pressure_resolution_osr_512); //2ms per reading, 0.062mbar resolution
      //  barometricSensor.set_pressure_resolution(MS8607_pressure_resolution_osr_1024); //3ms per reading, 0.039mbar resolution
      //  barometricSensor.set_pressure_resolution(MS8607_pressure_resolution_osr_2048); //5ms per reading, 0.028mbar resolution
      //  barometricSensor.set_pressure_resolution(MS8607_pressure_resolution_osr_4096); //9ms per reading, 0.021mbar resolution
      barometricSensor.set_pressure_resolution(MS8607_pressure_resolution_osr_8192); //17ms per reading, 0.016mbar resolution
      // set the humidity resolution
      //int err = barometricSensor.set_humidity_resolution(MS8607_humidity_resolution_8b); // 8 bits
      //int err = barometricSensor.set_humidity_resolution(MS8607_humidity_resolution_10b); // 10 bits
      //int err = barometricSensor.set_humidity_resolution(MS8607_humidity_resolution_11b); // 11 bits
      int err = barometricSensor.set_humidity_resolution(MS8607_humidity_resolution_12b); // 12 bits
      if (err != MS8607_status_ok)
      {
        shell.print("Problem setting the MS8607 sensor humidity resolution. Error code = ");
        shell.println(err);
      }
      // Turn the humidity sensor heater OFF
      // The TE examples say that get_compensated_humidity and get_dew_point will only work if the heater is OFF
      err = barometricSensor.disable_heater();
      if (err != MS8607_status_ok)
      {
        shell.print("Problem disabling the MS8607 humidity sensor heater. Error code = ");
        shell.println(err);
      }
    }

  // digital light sensor
  TSL2561.init();

  // define the commands implemented
  shell.attach(Serial);
  shell.addCommand(F("id?"),script_id);
  shell.addCommand(F("what?"),what_connected);
  shell.addCommand(F("wind?"),read_wind);
  shell.addCommand(F("pht?"),read_pressure_humidity_temperature);  
  shell.addCommand(F("light?"),read_light);
}

///////////////// functions which implement each command ////////////////

int script_id(int argc, char **argv){
  shell.println(F("Running " __FILE__ ", Built " __DATE__));
}


int what_connected(int argc, char **argv){
  shell.println("anemometer and vane - can't really say");
  if (barometricSensor.isConnected()) {
    shell.println("MS8607 barometer/termometer/hygrometer");
  }
    shell.println("TSL2561 digital light/IR sensor - can't really say");
} 

int read_wind(int argc, char **argv){
  // print out the values
  float angle=windangle();
  shell.print("v="); shell.print(wspeed,2); shell.print(" m/s  ");
  shell.print("dir. "); shell.print(angle,1); shell.println("°");
}

int read_pressure_humidity_temperature(int argc, char **argv){
  float temperature = barometricSensor.getTemperature();
  float pressure = barometricSensor.getPressure();
  float humidity = barometricSensor.getHumidity();
  float compensated_RH;
  int err = barometricSensor.get_compensated_humidity(temperature, humidity, &compensated_RH);
  float dew_point;
  err = barometricSensor.get_dew_point(temperature, humidity, &dew_point);
  shell.print("P:");shell.print(pressure,2); shell.print("hPa");
  shell.print(" T:");shell.print(temperature,2); shell.print("°C");
  shell.print(" RH:");shell.print(humidity,2); shell.print("%");
  shell.print(" comp RH:");shell.print(compensated_RH,2); shell.print("%");
  shell.print(" dew point:");shell.print(dew_point,2); shell.println("°C");
}


int read_light(int argc, char **argv){
  float temp_hum_val[2] = {0};
  shell.print(F("TSL vis(Lux) IR(luminosity): "));
  shell.print(TSL2561.readVisibleLux()); shell.print(SPC); shell.println(TSL2561.readIRLuminosity(),3);
}

//////////// Loop /////////////////////

void loop() {
   //characters are processed one at a time I think, this has to be executed as often as possible
  shell.executeIfInput();
}

// the interrupt routine, measuring the time since previous call
void elapsed() {
  unsigned int tnow=micros();
  wspeed=vcal/(tnow-tprevious); // wraparound uint32 should be taken care automatically
  tprevious=tnow;
}

void resetElapsed() {
  if (micros()-tprevious>Tmeas) {wspeed=0;}
}

////// data ancillaries /////

float windangle() {
  // Nominally the analog range should cover 0-5V with 0-1023, but instead it is seen
  //  to fit 0-3.3V.
  float angle = 360*(analogRead(VanePin) -1024*0.05 -2)/(1024*0.9);
  return angle;
}
