/**
 * I2C Scanner for XIAO ESP32S3
 * Scans for I2C devices and reports their addresses
 */

#include <Arduino.h>
#include <Wire.h>

#define SDA_PIN 5
#define SCL_PIN 6
#define LED_PIN 21

void setup() {
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  
  Serial.begin(115200);
  delay(2000);
  
  Serial.println("========================================");
  Serial.println("I2C Scanner - XIAO ESP32S3");
  Serial.println("========================================");
  Serial.println("SDA: GPIO5 (D4)");
  Serial.println("SCL: GPIO6 (D5)");
  Serial.println("========================================");
  Serial.println("");
  
  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(400000);  // 400kHz
  
  Serial.println("Scanning I2C bus...");
  Serial.println("");
}

void loop() {
  byte error, address;
  int nDevices = 0;
  
  Serial.println("Scanning for I2C devices...");
  
  for(address = 1; address < 127; address++ ) {
    Wire.beginTransmission(address);
    error = Wire.endTransmission();
    
    if (error == 0) {
      Serial.print("I2C device found at address 0x");
      if (address < 16) {
        Serial.print("0");
      }
      Serial.print(address, HEX);
      Serial.println(" !");
      
      // Blink LED when device found
      digitalWrite(LED_PIN, HIGH);
      delay(100);
      digitalWrite(LED_PIN, LOW);
      
      nDevices++;
      
      // Identify common sensors
      if (address == 0x68 || address == 0x69) {
        Serial.println("  -> Likely ICM-20948 or MPU-6050");
      }
    }
    else if (error == 4) {
      Serial.print("Unknown error at address 0x");
      if (address < 16) {
        Serial.print("0");
      }
      Serial.println(address, HEX);
    }    
  }
  
  if (nDevices == 0) {
    Serial.println("No I2C devices found!");
    Serial.println("");
    Serial.println("Check connections:");
    Serial.println("- SDA -> GPIO5 (D4)");
    Serial.println("- SCL -> GPIO6 (D5)");
    Serial.println("- VCC -> 3.3V");
    Serial.println("- GND -> GND");
  }
  else {
    Serial.println("");
    Serial.print("Found ");
    Serial.print(nDevices);
    Serial.println(" device(s)");
  }
  
  Serial.println("========================================");
  Serial.println("");
  
  delay(5000);  // Wait 5 seconds before next scan
}
