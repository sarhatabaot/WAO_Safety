/*
  Read wind speed and direction from Inspeed cup anemometer and vane.
  
  The e-vane is supplied by the 3.3V line, and provides an analog signal for the range 0-360°.
  Its output is connected to analog0. Nominally this is said to give an analog signal from
  5%*Vs to 95%Vs, i.e. 0.165-3.135V. However, that is seen to cover the full a0 range on the
  Seeeduino cortex M0+ (which should be nominally 0-5V). Supplying it with the board 5V line
  instead, it saturates the a0 input.

  The cup anemometer is connected to digital 0. We have the D3 rotor, which should provide
  1 pulse per turn, and 1 turn/sec per 1.207008m/sec. We measure the frequency counting pulses
  on d0. It would be nice if I could use a library like FreqMeasure, but unfortunately it doesn't
  support the Seeeduino Cortex M0+ SAM D21 which I'm using now. So I do it in a dummy way,
  polling continuously the digital pin....
  Operationally, I'd expect 0.5 to 100 turns per second, at most. The Hall sensor conducts
  for about 1/4 of the turn, which means that one has to detect a 0 pulse which could last
  from 2.5 to 500ms.
  
*/
const int AnemometerPin = 0;
const int Tmeas=4000000; // microsec

// the setup routine runs once when you press reset:
void setup() {
  // initialize the anemometer pin as a input:
  pinMode(AnemometerPin, INPUT);
  // initialize serial communication at 9600 bits per second:
  Serial.begin(9600);
}

// the loop routine runs over and over again forever:
void loop() {
  unsigned long t1=micros();
  unsigned int pulses=0;
  bool pinState1=true, pinState2; // with pullup resistor, the normal state is 1
  // for Tmeas, poll dumbly the anemometer pin and detect a rising transition
  while (micros()-t1 < Tmeas)
  {
      pinState2 = digitalRead(AnemometerPin);
      if (~pinState1 & pinState2)
         {pulses=pulses+1;}
      pinState1=pinState2;
  }
  // Serial.println(pulses);
  float wspeed=float(pulses)*1207008/float(Tmeas);
  
  // read the input on analog pin 0:
  int sensorValue = analogRead(A0);
  // Nominally the analog range should cover 0-5V with 0-1023, but instead it is seen
  //  to fit 0-3.3V.
  float angle = 360*(sensorValue -1024*0.05 -2)/(1024*0.9);
  // print out the values
  Serial.print("v="); Serial.print(wspeed,1); Serial.print("m/s  ");
  Serial.print("dir. "); Serial.print(angle,1); Serial.println("°");
}
