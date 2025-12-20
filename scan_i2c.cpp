/**
 * I2C Scanner for ESP32
 * This will scan the I2C bus and report all detected devices
 * Upload this temporarily to check which address your ICM-20948 is using
 */

#include <Arduino.h>
#include <Wire.h>

#define SDA_PIN 5
#define SCL_PIN 6

void setup() {
  Serial.begin(115200);
  delay(2000);
  
  Serial.println("\n\n=================================");
  Serial.println("I2C Scanner for XIAO ESP32S3");
  Serial.println("SDA = GPIO5, SCL = GPIO6");
  Serial.println("=================================\n");
  
  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(400000);
  
  Serial.println("Scanning I2C bus...\n");
  
  byte count = 0;
  
  for (byte i = 1; i < 127; i++) {
    Wire.beginTransmission(i);
    byte error = Wire.endTransmission();
    
    if (error == 0) {
      Serial.print("Device found at address 0x");
      if (i < 16) Serial.print("0");
      Serial.print(i, HEX);
      Serial.print(" (");
      Serial.print(i);
      Serial.print(")");
      
      // Identify known devices
      if (i == 0x68 || i == 0x69) {
        Serial.print(" - ICM-20948 (AD0=");
        Serial.print(i == 0x68 ? "LOW/0" : "HIGH/1");
        Serial.print(")");
      }
      
      Serial.println();
      count++;
    }
  }
  
  Serial.println("\n---------------------------------");
  Serial.print("Scan complete. Found ");
  Serial.print(count);
  Serial.println(" device(s).");
  Serial.println("---------------------------------\n");
  
  if (count == 0) {
    Serial.println("⚠ WARNING: No I2C devices found!");
    Serial.println("\nCheck:");
    Serial.println("  • Wiring: SDA→GPIO5, SCL→GPIO6");
    Serial.println("  • Power: 3.3V and GND connected");
    Serial.println("  • Connections are secure");
  } else {
    Serial.println("\nFor ICM-20948:");
    Serial.println("  • If found at 0x68 → Set AD0_VAL = 0 in main.cpp");
    Serial.println("  • If found at 0x69 → Set AD0_VAL = 1 in main.cpp");
  }
}

void loop() {
  delay(5000);
  Serial.println("\nScanning again in 5 seconds...");
  delay(5000);
  setup();
}
