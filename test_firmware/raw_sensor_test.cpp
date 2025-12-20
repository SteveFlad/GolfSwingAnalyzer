/**
 * Simple ICM-20948 Raw Data Test
 * Tests if the Adafruit library can read raw sensor data
 */

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_ICM20X.h>
#include <Adafruit_ICM20948.h>
#include <Adafruit_Sensor.h>

Adafruit_ICM20948 icm;

#define SDA_PIN 5
#define SCL_PIN 6
#define LED_PIN 21

void setup() {
  pinMode(LED_PIN, OUTPUT);
  Serial.begin(115200);
  delay(2000);
  
  Serial.println("ICM-20948 Raw Data Test");
  Serial.println("========================");
  
  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(400000);
  
  if (!icm.begin_I2C(0x68, &Wire) && !icm.begin_I2C(0x69, &Wire)) {
    Serial.println("Failed to find ICM20948!");
    while (1) delay(10);
  }
  
  Serial.println("ICM-20948 found!");
  
  // Configure
  icm.setAccelRange(ICM20948_ACCEL_RANGE_16_G);
  icm.setGyroRange(ICM20948_GYRO_RANGE_2000_DPS);
  
  Serial.println("Ready! Move the sensor...");
  Serial.println();
  digitalWrite(LED_PIN, HIGH);
}

void loop() {
  sensors_event_t accel, gyro, mag, temp;
  
  // Read sensor - force read every time
  icm.getEvent(&accel, &gyro, &temp, &mag);
  
  // Print everything
  Serial.print("Accel XYZ: ");
  Serial.print(accel.acceleration.x, 3); Serial.print(", ");
  Serial.print(accel.acceleration.y, 3); Serial.print(", ");
  Serial.print(accel.acceleration.z, 3);
  
  Serial.print("  |  Gyro XYZ: ");
  Serial.print(gyro.gyro.x, 3); Serial.print(", ");
  Serial.print(gyro.gyro.y, 3); Serial.print(", ");
  Serial.print(gyro.gyro.z, 3);
  
  Serial.print("  |  Temp: ");
  Serial.println(temp.temperature, 2);
  
  delay(100);  // 10Hz for readability
}
