/**
 * Golf Swing Analyzer - ESP32 Firmware with BLE Support
 * 
 * Hardware:
 * - Board: XIAO ESP32S3
 * - Sensor: ICM-20948 9-DOF IMU (GY-ICM20948V2)
 * - Connection: I2C (SDA=GPIO5, SCL=GPIO6)
 * 
 * Uses Adafruit ICM20X library with Madgwick filter for quaternion calculation
 * Outputs quaternion data via USB Serial and BLE GATT
 * Format: Q0:w Q1:x Q2:y Q3:z
 */

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_ICM20X.h>
#include <Adafruit_ICM20948.h>
#include <Adafruit_Sensor.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// Create sensor object
Adafruit_ICM20948 icm;

// BLE Objects
BLEServer* pServer = nullptr;
BLECharacteristic* pCharacteristic = nullptr;
bool deviceConnected = false;
bool oldDeviceConnected = false;

// BLE UUIDs (match Python ble_capture.py)
#define SERVICE_UUID        "12345678-1234-1234-1234-123456789abc"
#define CHARACTERISTIC_UUID "87654321-4321-4321-4321-cba987654321"
#define DEVICE_NAME         "GolfSwingAnalyzer"

// I2C configuration for XIAO ESP32S3
#define SDA_PIN 5
#define SCL_PIN 6
#define LED_PIN 21

// Configuration
#define SERIAL_BAUD 115200
#define SAMPLE_RATE_HZ 100

// Madgwick filter variables
float q0 = 1.0f, q1 = 0.0f, q2 = 0.0f, q3 = 0.0f;
float beta = 0.5f;  // Filter gain (increased for faster response)
unsigned long lastUpdate = 0;
int sampleCount = 0;

// BLE Server Callbacks
class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
      deviceConnected = true;
      Serial.println("BLE Client Connected!");
    };

    void onDisconnect(BLEServer* pServer) {
      deviceConnected = false;
      Serial.println("BLE Client Disconnected");
      // Restart advertising so new clients can connect
      BLEDevice::startAdvertising();
      Serial.println("BLE Advertising restarted");
    }
};

void blinkLED(int times, int delayMs = 100) {
  for (int i = 0; i < times; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(delayMs);
    digitalWrite(LED_PIN, LOW);
    delay(delayMs);
  }
}

// Madgwick AHRS algorithm update (6DOF - no magnetometer)
void MadgwickQuaternionUpdate(float ax, float ay, float az, float gx, float gy, float gz, float dt) {
  float recipNorm;
  float s0, s1, s2, s3;
  float qDot1, qDot2, qDot3, qDot4;
  float _2q0, _2q1, _2q2, _2q3, _4q0, _4q1, _4q2, _8q1, _8q2, q0q0, q1q1, q2q2, q3q3;

  // Rate of change of quaternion from gyroscope
  qDot1 = 0.5f * (-q1 * gx - q2 * gy - q3 * gz);
  qDot2 = 0.5f * (q0 * gx + q2 * gz - q3 * gy);
  qDot3 = 0.5f * (q0 * gy - q1 * gz + q3 * gx);
  qDot4 = 0.5f * (q0 * gz + q1 * gy - q2 * gx);

  // Compute feedback only if accelerometer measurement valid (avoids NaN in accelerometer normalisation)
  if (!((ax == 0.0f) && (ay == 0.0f) && (az == 0.0f))) {
    // Normalise accelerometer measurement
    recipNorm = 1.0f / sqrt(ax * ax + ay * ay + az * az);
    ax *= recipNorm;
    ay *= recipNorm;
    az *= recipNorm;

    // Auxiliary variables to avoid repeated arithmetic
    _2q0 = 2.0f * q0;
    _2q1 = 2.0f * q1;
    _2q2 = 2.0f * q2;
    _2q3 = 2.0f * q3;
    _4q0 = 4.0f * q0;
    _4q1 = 4.0f * q1;
    _4q2 = 4.0f * q2;
    _8q1 = 8.0f * q1;
    _8q2 = 8.0f * q2;
    q0q0 = q0 * q0;
    q1q1 = q1 * q1;
    q2q2 = q2 * q2;
    q3q3 = q3 * q3;

    // Gradient decent algorithm corrective step
    s0 = _4q0 * q2q2 + _2q2 * ax + _4q0 * q1q1 - _2q1 * ay;
    s1 = _4q1 * q3q3 - _2q3 * ax + 4.0f * q0q0 * q1 - _2q0 * ay - _4q1 + _8q1 * q1q1 + _8q1 * q2q2 + _4q1 * az;
    s2 = 4.0f * q0q0 * q2 + _2q0 * ax + _4q2 * q3q3 - _2q3 * ay - _4q2 + _8q2 * q1q1 + _8q2 * q2q2 + _4q2 * az;
    s3 = 4.0f * q1q1 * q3 - _2q1 * ax + 4.0f * q2q2 * q3 - _2q2 * ay;
    
    recipNorm = 1.0f / sqrt(s0 * s0 + s1 * s1 + s2 * s2 + s3 * s3);
    s0 *= recipNorm;
    s1 *= recipNorm;
    s2 *= recipNorm;
    s3 *= recipNorm;

    // Apply feedback step
    qDot1 -= beta * s0;
    qDot2 -= beta * s1;
    qDot3 -= beta * s2;
    qDot4 -= beta * s3;
  }

  // Integrate rate of change of quaternion to yield quaternion
  q0 += qDot1 * dt;
  q1 += qDot2 * dt;
  q2 += qDot3 * dt;
  q3 += qDot4 * dt;

  // Normalise quaternion
  recipNorm = 1.0f / sqrt(q0 * q0 + q1 * q1 + q2 * q2 + q3 * q3);
  q0 *= recipNorm;
  q1 *= recipNorm;
  q2 *= recipNorm;
  q3 *= recipNorm;
}

void setup() {
  // Initialize LED
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  
  // Initialize Serial
  Serial.begin(SERIAL_BAUD);
  delay(2000);
  
  Serial.println("========================================");
  Serial.println("Golf Swing Analyzer - ESP32 Firmware");
  Serial.println("Board: XIAO ESP32S3");
  Serial.println("Sensor: ICM-20948 (Adafruit Library)");
  Serial.println("Mode: USB Serial + BLE GATT");
  Serial.println("========================================");
  
  // Initialize BLE
  Serial.println("Initializing BLE...");
  BLEDevice::init(DEVICE_NAME);
  
  // Create BLE Server
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());
  
  // Configure connection parameters for stability
  // Min interval: 10ms, Max interval: 20ms, Latency: 0, Timeout: 4000ms
  BLEDevice::setMTU(512);  // Increase MTU for better throughput
  
  // Create BLE Service
  BLEService *pService = pServer->createService(SERVICE_UUID);
  
  // Create BLE Characteristic
  pCharacteristic = pService->createCharacteristic(
                      CHARACTERISTIC_UUID,
                      BLECharacteristic::PROPERTY_READ |
                      BLECharacteristic::PROPERTY_NOTIFY
                    );
  
  // Add Client Characteristic Configuration Descriptor (required for notifications)
  pCharacteristic->addDescriptor(new BLE2902());
  
  // Start the service
  pService->start();
  
  // Start advertising with device name
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(true);
  pAdvertising->setMinPreferred(0x06);  // Functions that help with iPhone connections
  pAdvertising->setMinPreferred(0x12);
  
  // Add device name to advertising data (this makes it visible in scans)
  BLEAdvertisementData advertisementData;
  advertisementData.setName(DEVICE_NAME);
  advertisementData.setCompleteServices(BLEUUID(SERVICE_UUID));
  pAdvertising->setAdvertisementData(advertisementData);
  
  BLEDevice::startAdvertising();
  
  Serial.print("BLE Device Name: ");
  Serial.println(DEVICE_NAME);
  Serial.println("BLE Advertising started - device is discoverable");
  blinkLED(3, 100);
  
  // Initialize I2C
  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(400000);
  
  Serial.println("Initializing ICM-20948...");
  blinkLED(2);
  
  // Try to initialize sensor
  if (!icm.begin_I2C(0x68, &Wire)) {
    // Try alternate address
    if (!icm.begin_I2C(0x69, &Wire)) {
      Serial.println("========================================");
      Serial.println("ERROR: Failed to find ICM-20948!");
      Serial.println("Check wiring:");
      Serial.println("  SDA → GPIO5 (D4)");
      Serial.println("  SCL → GPIO6 (D5)");
      Serial.println("  VCC → 3.3V");
      Serial.println("  GND → GND");
      Serial.println("========================================");
      while (1) {
        blinkLED(5, 50);
        delay(1000);
      }
    }
  }
  
  Serial.println("ICM-20948 found!");
  
  // Configure sensor ranges  
  Serial.println("Configuring sensor...");
  icm.setAccelRange(ICM20948_ACCEL_RANGE_16_G);  // Try higher range for golf swings
  Serial.print("Accelerometer range: ±");
  switch (icm.getAccelRange()) {
    case ICM20948_ACCEL_RANGE_2_G: Serial.println("2G"); break;
    case ICM20948_ACCEL_RANGE_4_G: Serial.println("4G"); break;
    case ICM20948_ACCEL_RANGE_8_G: Serial.println("8G"); break;
    case ICM20948_ACCEL_RANGE_16_G: Serial.println("16G"); break;
  }
  
  icm.setGyroRange(ICM20948_GYRO_RANGE_2000_DPS);  // Try higher range for golf swings
  Serial.print("Gyroscope range: ±");
  switch (icm.getGyroRange()) {
    case ICM20948_GYRO_RANGE_250_DPS: Serial.println("250 dps"); break;
    case ICM20948_GYRO_RANGE_500_DPS: Serial.println("500 dps"); break;
    case ICM20948_GYRO_RANGE_1000_DPS: Serial.println("1000 dps"); break;
    case ICM20948_GYRO_RANGE_2000_DPS: Serial.println("2000 dps"); break;
  }
  
  // Set data rate
  icm.setAccelRateDivisor(10);  // ~100Hz
  icm.setGyroRateDivisor(10);   // ~100Hz
  
  Serial.println("Testing sensor readings...");
  delay(500);  // Give sensor time to stabilize
  
  // Test readings
  for (int i = 0; i < 3; i++) {
    sensors_event_t accel, gyro, mag, temp;
    if (icm.getEvent(&accel, &gyro, &temp, &mag)) {
      Serial.print("  Test ");
      Serial.print(i+1);
      Serial.print(": AX=");
      Serial.print(accel.acceleration.x, 2);
      Serial.print(" AY=");
      Serial.print(accel.acceleration.y, 2);
      Serial.print(" AZ=");
      Serial.print(accel.acceleration.z, 2);
      Serial.print(" | GX=");
      Serial.print(gyro.gyro.x, 2);
      Serial.print(" GY=");
      Serial.print(gyro.gyro.y, 2);
      Serial.print(" GZ=");
      Serial.println(gyro.gyro.z, 2);
    }
    delay(100);
  }
  
  Serial.println("========================================");
  Serial.println("READY! Streaming quaternions...");
  Serial.println("Format: Q0:w Q1:x Q2:y Q3:z");
  Serial.println("========================================");
  
  digitalWrite(LED_PIN, HIGH);
  lastUpdate = millis();
}

void loop() {
  sensors_event_t accel, gyro, mag, temp;
  
  // Handle BLE connection state changes
  if (!deviceConnected && oldDeviceConnected) {
    delay(500); // Give BLE stack time to prepare
    oldDeviceConnected = deviceConnected;
  }
  if (deviceConnected && !oldDeviceConnected) {
    oldDeviceConnected = deviceConnected;
  }
  
  // Read sensor data with error checking
  bool success = icm.getEvent(&accel, &gyro, &temp, &mag);
  
  if (!success) {
    // If read failed, skip this iteration
    delay(10);
    return;
  }
  
  unsigned long now = millis();
  float dt = (now - lastUpdate) / 1000.0f;
  lastUpdate = now;
  
  // Get accelerometer data (m/s²)
  float ax = accel.acceleration.x;
  float ay = accel.acceleration.y;
  float az = accel.acceleration.z;
  
  // Get gyroscope data (rad/s)
  float gx = gyro.gyro.x;
  float gy = gyro.gyro.y;
  float gz = gyro.gyro.z;
  
  // Check if we got valid data (not all zeros)
  if (ax == 0.0f && ay == 0.0f && az == 0.0f && 
      gx == 0.0f && gy == 0.0f && gz == 0.0f) {
    // All zeros - bad read, skip this sample
    delay(10);
    return;
  }
  
  // Debug: Print raw sensor data every 100 samples
  sampleCount++;
  if (sampleCount % 100 == 0) {
    Serial.print("[DEBUG] Accel: ");
    Serial.print(ax, 2); Serial.print(" ");
    Serial.print(ay, 2); Serial.print(" ");
    Serial.print(az, 2);
    Serial.print(" | Gyro: ");
    Serial.print(gx, 2); Serial.print(" ");
    Serial.print(gy, 2); Serial.print(" ");
    Serial.println(gz, 2);
  }
  
  // Update quaternion using Madgwick filter
  if (dt > 0.001f && dt < 1.0f) {  // Valid time delta
    MadgwickQuaternionUpdate(ax, ay, az, gx, gy, gz, dt);
    
    // Format quaternion data
    char buffer[100];
    snprintf(buffer, sizeof(buffer), "Q0:%.4f Q1:%.4f Q2:%.4f Q3:%.4f", q0, q1, q2, q3);
    
    // Send to USB Serial
    Serial.println(buffer);
    
    // Send to BLE if client is connected
    if (deviceConnected) {
      pCharacteristic->setValue(buffer);
      pCharacteristic->notify();
      // Blink LED to show BLE activity
      if (sampleCount % 10 == 0) {
        digitalWrite(LED_PIN, !digitalRead(LED_PIN));
      }
    } else {
      digitalWrite(LED_PIN, HIGH);  // Solid LED when no BLE client
    }
    
    // Small delay to prevent overwhelming BLE stack
    delayMicroseconds(500);  // 0.5ms delay
  }
  
  delay(15);  // Slow down slightly to reduce I2C errors (~66Hz)
}
