// Libraries

#include <SimpleSerialShell.h>

// Definitions

#define SENSOR1 A0
#define SPC F(" ") // feels a little idiot

// Functions

int script_id(int argc, char **argv){
  shell.println(F("Running " __FILE__ ", Built " __DATE__));
}

int read_temperatures(int argc, char **argv){
  int A;
  float T1;
  const int B=4275; // The B constant of the thermoresistor, according to the datasheet
                    //  in another place I have B=3975;
  float resistance;

  A=analogRead(SENSOR1);
  resistance=(float)(1023-A)*100000/A; //get the resistance of the sensor; (somewhere else *10000)
  T1=1/(log(resistance/100000)/B+1/298.15)-273.15;//convert to temperature via datasheet; 

  shell.print(F("Temperature: ")); shell.println(T1);
}

//////////////// Setup and Loop ///////////////////////

void setup(){
  Serial.begin(115200); // Set the baud rate (bits per second)
  
  while (!Serial); // Wait for serial
  
  shell.attach(Serial);
  shell.addCommand(F("id?"),script_id);
  shell.addCommand(F("temp?"),read_temperatures);
}

void loop(){
  shell.executeIfInput();
}
