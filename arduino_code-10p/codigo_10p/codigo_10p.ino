#include <Wire.h>
#include "MAX30105.h"
#include "heartRate.h"

MAX30105 particleSensor;

const byte RATE_SIZE = 4;
byte rates[4][RATE_SIZE];
byte rateSpot[4];
long lastBeat[4];
float beatsPerMinute[4];
int beatAvg[4];

void setup() {
  Serial.begin(115200);

  for (int i = 0; i < 4; i++) {
    rateSpot[i] = 0;
    lastBeat[i] = 0;
    if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
      Serial.println("MAX30105 not found. Please check wiring/power.");
      while (1);
    }
    particleSensor.setup();
    particleSensor.setPulseAmplitudeRed(0x0A);
    particleSensor.setPulseAmplitudeGreen(0);
  }
}

void loop() {
  for (int i = 0; i < 4; i++) {
    long irValue = particleSensor.getIR();
    int GSR = analogRead(i); // Assume GSR sensors are connected to A0-A3

    if (checkForBeat(irValue)) {
      long delta = millis() - lastBeat[i];
      lastBeat[i] = millis();
      beatsPerMinute[i] = 60 / (delta / 1000.0);

      if (beatsPerMinute[i] < 255 && beatsPerMinute[i] > 20) {
        rates[i][rateSpot[i]++] = (byte)beatsPerMinute[i];
        rateSpot[i] %= RATE_SIZE;
        beatAvg[i] = 0;
        for (byte x = 0; x < RATE_SIZE; x++) {
          beatAvg[i] += rates[i][x];
        }
        beatAvg[i] /= RATE_SIZE;
      }
    }
    Serial.println();
    Serial.print((int)beatsPerMinute[i]);
    Serial.print(",");
    Serial.print(beatAvg[i]);
    Serial.print(",");
    Serial.print(GSR); // GSR
  }
  delay(50); // Small delay to avoid overwhelming the serial buffer
}
