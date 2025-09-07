#define SENSOR1 A0

int a;
float temp;
const int B=4275; // The B constant of the thermoresistor, according to the datasheet

void setup() {
  Serial.begin(9600); // Baud rate 9600
}

void loop() {
  a = analogRead(SENSOR1); // Read the analog input of the thermoresistor
  float R = 1023.0/((float)a)-1.0; // Temperature conversion to C
  temp = 1.0/(log(R)/B+1/298.15)-273.15; // Temperature conversion to C
  Serial.println(temp);
  delay(100);
}
