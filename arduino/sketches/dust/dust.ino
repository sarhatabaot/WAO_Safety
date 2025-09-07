int pin = D2;
unsigned long duration, pulsecount=0;
unsigned long starttime;
unsigned long sampletime_ms = 5000;//sampe 10s ;
unsigned long lowpulseoccupancy = 0;
float ratio = 0;
float concentration = 0;
 
void setup() 
{
    Serial.begin(115200);
    pinMode(pin,INPUT);
    starttime = millis();//get the current time;
}
 
void loop() 
{
    pulsecount++;
    duration = pulseIn(pin, LOW);
    lowpulseoccupancy = lowpulseoccupancy+duration;
 
    if ((millis()-starttime) > sampletime_ms)//if the sampel time == 30s
    {
        ratio = lowpulseoccupancy/(sampletime_ms*10.0);  // Integer percentage 0=>100
        concentration = 1.1*pow(ratio,3)-3.8*pow(ratio,2)+520*ratio+0.62; // using spec sheet curve
        Serial.print(millis()/1000.0);
        Serial.print(" -- ");
        Serial.print(pulsecount); Serial.print(" pulses:");
        Serial.print(lowpulseoccupancy);
        Serial.print("us, ");
        Serial.print(ratio);
        Serial.print("%, ");
        Serial.print(concentration);
        Serial.println("p/l");
        lowpulseoccupancy = 0;
        pulsecount = 0;
        starttime = millis();
    }
}
