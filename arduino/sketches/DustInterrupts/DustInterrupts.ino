// test reading the Grove dust sensor using interrupts

#include <TimerTC3.h>
#include <SimpleSerialShell.h>


const int DustPin = 2;
const int Tmeas = 20000000; // microsec
volatile unsigned long tdown, lowPulseOccupancy, lastOccupancy, imeas, pulsecount;

void setup() {
  pinMode(DustPin, INPUT);
  // interrupts to start and stop lowPulseOccupancy accumulation
  attachInterrupt(digitalPinToInterrupt(DustPin), dustTransit, CHANGE);
  //interrupt to reset measure after Tmeas
  TimerTc3.initialize(Tmeas);
  TimerTc3.attachInterrupt(resetMeasure);
  Serial.begin(115200);
  while (!Serial)
  {
  };
  // define the commands implemented
  shell.attach(Serial);
  shell.addCommand(F("id?"), script_id);
  shell.addCommand(F("dust?"), report_last_dust);
}

void loop() {
  //characters are processed one at a time I think, this has to be executed as often as possible
  shell.executeIfInput();
  delay(1000);
  report_last_dust(NULL, NULL);
}


///////////////// functions which implement each command ////////////////

int script_id(int argc, char **argv) {
  shell.println(F("Running " __FILE__ ", Built " __DATE__));
}

int report_last_dust(int argc, char **argv) {
  // convert the last total down time to particles/liter using spec sheet curve
  float ratio = 100 * float(lastOccupancy) / float(Tmeas); // percentage 0=>100
  float partconc = 1.1 * pow(ratio, 3) - 3.8 * pow(ratio, 2) + 520 * ratio + 0.62;
  shell.print(imeas);
  shell.print(" pulses:"); shell.print(pulsecount);
  shell.print(" occ:"); shell.print(lastOccupancy);
  shell.print(" ratio:"); shell.print(ratio);
  shell.print("% C:"); shell.print(partconc); shell.println(" part/l");
}


// interrupt routines

void dustTransit() {
  // single interrupt routine for both FALLING and RISING. Two interrupts
  //  for the two events on the same pin doesn't seem to work
  if (digitalRead(DustPin)) {
    lowPulseOccupancy = lowPulseOccupancy + (micros() - tdown);
  }
  else {
    pulsecount++;
    tdown = micros();
  }
}

void resetMeasure() {
  // copy the total pulse down time as last measurement and reset the accumulator
  lastOccupancy = lowPulseOccupancy;
  imeas++;
  lowPulseOccupancy = 0;
  pulsecount = 0;
}
