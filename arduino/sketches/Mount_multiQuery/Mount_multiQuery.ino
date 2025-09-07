/////////// used libraries and card definitions: ///////////////////

#include <SimpleSerialShell.h>

#include "BMI088.h"

#include "LIS3DHTR.h"
LIS3DHTR<TwoWire> LIS; //IIC
#define WIRE Wire

#include "DHT.h"
#define DHTPIN 3     // what pin we're connected to 
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

#define WETPIN 2  // water sensor connected as digital

#define PIEZOPIN 4  // piezo vibration/flex sensor as digital
boolean vibr=false;

#include <Digital_Light_TSL2561.h>

#include <Statistic.h>

Statistic accelstats[2];
#define ACCUPDATE 50 // milliseconds

#define NAN "NaN"
#define CONNECTED F("connected")
#define UNCONNECTED F("didn't connect")
#define SPC F(" ") // feels a little idiot

///////////////// functions which implement each command ////////////////

int script_id(int argc, char **argv){
  shell.println(F("Running " __FILE__ ", Built " __DATE__));
}


int what_connected(int argc, char **argv){
  shell.print(F("LIS3DHTR "));
  if (LIS)
  {
    shell.println(CONNECTED);
  }  else {  
    shell.println(UNCONNECTED);
  }

  shell.print(F("BMI088 "));
  if (bmi088.isConnection()) {
            shell.println(CONNECTED);
        } else {
            shell.println(UNCONNECTED);
        }
}


int read_temperatures(int argc, char **argv){
  int A;
  float T1, T2;
  int B=3975;                  //B value of the thermistor
  float resistance;
  float temp_hum_val[2] = {0};

  A=analogRead(0);
  resistance=(float)(1023-A)*10000/A; //get the resistance of the sensor;
  T1=1/(log(resistance/10000)/B+1/298.15)-273.15;//convert to temperature via datasheet;
  A=analogRead(2);
  resistance=(float)(1023-A)*10000/A; //get the resistance of the sensor;
  T2=1/(log(resistance/10000)/B+1/298.15)-273.15;//convert to temperature via datasheet;
  
  shell.print(F("NTC1,NTC2,LIS,BMI,DHT: ")); shell.print(T1); shell.print(SPC); shell.print(T2);
  shell.print(SPC); shell.print(LIS.getTemperature());
  shell.print(SPC); shell.print(bmi088.getTemperature());
  shell.print(SPC); shell.println(dht.readTemperature(false));
}


int read_accelerations(int argc, char **argv){
  // unsigned long t1=millis();
  float bx = 0, by = 0, bz = 0;

  bmi088.getAcceleration(&bx, &by, &bz);

  shell.print(F("LIS,BMI x y z: "));
  shell.print(LIS.getAccelerationX(),3); shell.print(SPC);
  shell.print(LIS.getAccelerationY(),3); shell.print(SPC);
  shell.print(LIS.getAccelerationZ(),3); shell.print(SPC);
  shell.print(bx/1000,3); shell.print(SPC); shell.print(by/1000,3); shell.print(SPC); shell.println(bz/1000,3);
  
  // shell.print(F("   printed in ")); shell.print(millis()-t1); shell.println(F("ms"));
}


int read_acceleration_statistics(int argc, char **argv){
  shell.print(F("LISavgdev,LISmaxdev,BMIavgdev,BMImaxdev: "));
  shell.print(accelstats[0].average(),4); shell.print(SPC); shell.print(accelstats[0].maximum(),4); shell.print(SPC); 
  shell.print(accelstats[1].average(),4); shell.print(SPC); shell.println(accelstats[1].maximum(),4); 
  accelstats[0].clear(); //reset
  accelstats[1].clear();
}


int read_gyroscope(int argc, char **argv){
  float gx = 0, gy = 0, gz = 0;
  bmi088.getGyroscope(&gx, &gy, &gz);
  
  shell.print(F("BMI gyr x y z: "));
  shell.print(gx,3); shell.print(SPC); shell.print(gy,3); shell.print(SPC); shell.println(gz,3);
}


int read_humidity(int argc, char **argv){
  float temp_hum_val[2] = {0};
  //unsigned long t1=millis();
  shell.print(F("DHT RH%: "));
  // the temp and humidiy code has long internal delays. Apparently 250ms+ time the readout has stabilized.
  shell.println(dht.readHumidity());
  //shell.print(F("   printed in ")); shell.print(millis()-t1); shell.println(F("ms"));
}


int read_light(int argc, char **argv){
  float temp_hum_val[2] = {0};
  shell.print(F("TSL vis(Lux) IR(luminosity): "));
  shell.print(TSL2561.readVisibleLux()); shell.print(SPC); shell.println(TSL2561.readIRLuminosity(),3);
}


int read_wet(int argc, char **argv){
  shell.print(F("Wet: ")); shell.println(!digitalRead(WETPIN));
}


int read_vibr(int argc, char **argv){
  //read and reset the vibration flag
  // very strange - vibr is read as true immediately after read_gyroscope and read_light (in this order)
  shell.print(F("Vibration: ")); shell.println(vibr);
  vibr=false;
}

//////////////// Setup and Loop ///////////////////////

void setup()
{
  Serial.begin(115200);
  while (!Serial)
  {
  };

  // define the commands implemented
  shell.attach(Serial);
  shell.addCommand(F("id?"),script_id);
  shell.addCommand(F("what?"),what_connected);
  shell.addCommand(F("temp?"),read_temperatures);
  shell.addCommand(F("acc?"),read_accelerations);
  shell.addCommand(F("accstat?"),read_acceleration_statistics);
  shell.addCommand(F("gyr?"),read_gyroscope);
  shell.addCommand(F("hum?"),read_humidity);
  shell.addCommand(F("light?"),read_light);
  shell.addCommand(F("wet?"),read_wet);
  shell.addCommand(F("vibr?"),read_vibr);

  // define mode of digital i/o
  pinMode(WETPIN, INPUT);

  // setup and initialize various digital sensors
  LIS.begin(WIRE, LIS3DHTR_ADDRESS_UPDATED); //IIC init
  LIS.openTemp();////If ADC3 is used, the temperature detection needs to be turned off.
  delay(100);
  LIS.setFullScaleRange(LIS3DHTR_RANGE_2G);
  LIS.setOutputDataRate(LIS3DHTR_DATARATE_10HZ);
  LIS.setHighSolution(true); //High solution enable

  Wire.begin();

  while (1) {
        if (bmi088.isConnection()) {
            bmi088.initialize();
            break;
        delay(2000);
        }
    }
    bmi088.setAccScaleRange(RANGE_3G);
    bmi088.setAccOutputDataRate(ODR_12);
    bmi088.setGyroScaleRange(RANGE_125);
    bmi088.setGyroOutputDataRate(ODR_100_BW_12);
    
    dht.begin();

    TSL2561.init();

    accelstats[0].clear(); //explicitly start clean
    accelstats[1].clear();
}


void loop()
{
  float ax = 0, ay = 0, az = 0;
  int tick = 0;

  // this is used as a trigger, the status has to be read often
  if (digitalRead(PIEZOPIN)) vibr=true;

  if (millis()-tick > ACCUPDATE) {
    // read accelerations at every step and accumulate statistics of deviations from 1g
    ax=LIS.getAccelerationX(); ay=LIS.getAccelerationY(); az=LIS.getAccelerationZ();
    accelstats[0].add( abs(sqrt(ax*ax+ay*ay+az*az)-1) );
    bmi088.getAcceleration(&ax, &ay, &az);
    accelstats[1].add( abs(sqrt(ax*ax+ay*ay+az*az)/1000-1) );
    tick=millis(); 
  }
  
  //characters are processed one at a time I think, this has to be executed as often as possible
  shell.executeIfInput();
}
