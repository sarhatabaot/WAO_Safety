/*
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

// the setup routine runs once when you press reset:
void setup() {
  // initialize the anemometer pin as a input:
  pinMode(AnemometerPin, INPUT);
  // interrupt to read deltaT since previous pulse
  attachInterrupt(digitalPinToInterrupt(AnemometerPin),elapsed,FALLING);
  //interrupt to reset deltaT if no new pulse arrived
  TimerTcc0.initialize(Tmeas);
  TimerTcc0.attachInterrupt(resetElapsed);
  // initialize serial communication at 9600 bits per second:
  Serial.begin(57600);
}

// the loop routine runs over and over again forever:
void loop() {
  delay(500);
    
  // print out the values
  float angle=windangle();
  Serial.print("v="); Serial.print(wspeed,2); Serial.print(" m/s  ");
  Serial.print("dir. "); Serial.print(angle,1); Serial.println("°");
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

float windangle() {
  // Nominally the analog range should cover 0-5V with 0-1023, but instead it is seen
  //  to fit 0-3.3V.
  float angle = 360*(analogRead(VanePin) -1024*0.05 -2)/(1024*0.9);
  return angle;
}
