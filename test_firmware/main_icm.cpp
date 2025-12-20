/**
 * Golf Swing Analyzer - ESP32 Firmware
 * 
 * Hardware:
 * - Board: XIAO ESP32S3
 * - Sensor: ICM-20948 9-DOF IMU
 * - Connection: I2C (SDA=GPIO5, SCL=GPIO6 on XIAO ESP32S3)
 * 
 * This firmware reads quaternion data from the ICM-20948's Digital Motion Processor (DMP)
 * and sends it over serial in the format expected by the Python visualizer:
 * Q0:0.123 Q1:-0.456 Q2:0.789 Q3:-0.012
 * 
 * The DMP provides 6-axis game rotation vectors (accelerometer + gyroscope fusion)
 * without requiring magnetometer calibration.
 */

#include <Arduino.h>
#include <Wire.h>
#include <ICM_20948.h>

// Create ICM_20948_I2C object
ICM_20948_I2C myICM;

// I2C configuration for XIAO ESP32S3
#define SDA_PIN 5
#define SCL_PIN 6
#define WIRE_PORT Wire
// AD0_VAL will be auto-detected (tries both 0x68 and 0x69 addresses)

// LED pin for status indication (XIAO ESP32S3 has built-in LED on GPIO21)
#define LED_PIN 21

// Configuration
#define SERIAL_BAUD 115200
#define I2C_SPEED 400000  // 400kHz I2C clock

void blinkLED(int times, int delayMs = 100) {
  for (int i = 0; i < times; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(delayMs);
    digitalWrite(LED_PIN, LOW);
    delay(delayMs);
  }
}

void setup() {
  // Initialize LED
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  
  // Initialize Serial
  Serial.begin(SERIAL_BAUD);
  delay(2000);  // Give time for serial monitor to connect
  
  Serial.println("========================================");
  Serial.println("Golf Swing Analyzer - ESP32 Firmware");
  Serial.println("Board: XIAO ESP32S3");
  Serial.println("Sensor: ICM-20948");
  Serial.println("========================================");
  
  // Initialize I2C on custom pins
  WIRE_PORT.begin(SDA_PIN, SCL_PIN);
  WIRE_PORT.setClock(I2C_SPEED);
  
  Serial.println("Initializing ICM-20948...");
  blinkLED(2);
  
  // Initialize the sensor - try both I2C addresses
  bool initialized = false;
  uint8_t detected_addr = 0;
  
  // Try address 0x69 first (AD0 = HIGH or floating)
  Serial.println("Trying address 0x69 (AD0=HIGH/floating)...");
  for (int i = 0; i < 2; i++) {
    myICM.begin(WIRE_PORT, 1);
    Serial.print("  Attempt ");
    Serial.print(i + 1);
    Serial.print(": ");
    Serial.println(myICM.statusString());
    
    if (myICM.status == ICM_20948_Stat_Ok) {
      initialized = true;
      detected_addr = 0x69;
      break;
    }
    delay(300);
  }
  
  // If not found, try address 0x68 (AD0 = LOW/GND)
  if (!initialized) {
    Serial.println("Trying address 0x68 (AD0=LOW/GND)...");
    for (int i = 0; i < 2; i++) {
      myICM.begin(WIRE_PORT, 0);
      Serial.print("  Attempt ");
      Serial.print(i + 1);
      Serial.print(": ");
      Serial.println(myICM.statusString());
      
      if (myICM.status == ICM_20948_Stat_Ok) {
        initialized = true;
        detected_addr = 0x68;
        break;
      }
      delay(300);
    }
  }
  
  if (!initialized) {
    Serial.println("========================================");
    Serial.println("ERROR: Failed to initialize ICM-20948!");
    Serial.println("========================================");
    Serial.println("Troubleshooting steps:");
    Serial.println("1. Check I2C connections:");
    Serial.println("   - SDA → GPIO5 (D4)");
    Serial.println("   - SCL → GPIO6 (D5)");
    Serial.println("2. Check power supply:");
    Serial.println("   - VCC → 3.3V");
    Serial.println("   - GND → GND");
    Serial.println("3. Check sensor is ICM-20948 (not similar model)");
    Serial.println("4. Try connecting AD0 to 3.3V or GND");
    Serial.println("========================================");
    while (1) {
      blinkLED(5, 50);  // Fast blinking indicates error
      delay(1000);
    }
  }
  
  Serial.println("========================================");
  Serial.print("ICM-20948 initialized successfully at 0x");
  Serial.println(detected_addr, HEX);
  Serial.println("========================================");
  blinkLED(3);
  
  // Initialize the DMP (Digital Motion Processor)
  Serial.println("Initializing DMP...");
  
  bool dmpSuccess = true;
  dmpSuccess &= (myICM.initializeDMP() == ICM_20948_Stat_Ok);
  
  // Enable Game Rotation Vector (6-axis quaternion: accel + gyro only)
  // This doesn't require magnetometer calibration
  dmpSuccess &= (myICM.enableDMPSensor(INV_ICM20948_SENSOR_GAME_ROTATION_VECTOR) == ICM_20948_Stat_Ok);
  
  // Set DMP output data rate
  // DMP_ODR_Reg_Quat6: Quaternion output rate register
  // Setting to 0 = maximum rate (~225 Hz)
  // Setting to 4 = ~45 Hz
  // For golf swing analysis, we want high speed: use 0 or 1
  dmpSuccess &= (myICM.setDMPODRrate(DMP_ODR_Reg_Quat6, 0) == ICM_20948_Stat_Ok);
  
  // Enable FIFO
  dmpSuccess &= (myICM.enableFIFO() == ICM_20948_Stat_Ok);
  
  // Enable DMP
  dmpSuccess &= (myICM.enableDMP() == ICM_20948_Stat_Ok);
  
  // Reset DMP and FIFO
  dmpSuccess &= (myICM.resetDMP() == ICM_20948_Stat_Ok);
  dmpSuccess &= (myICM.resetFIFO() == ICM_20948_Stat_Ok);
  
  if (dmpSuccess) {
    Serial.println("========================================");
    Serial.println("DMP ENABLED! Streaming quaternions...");
    Serial.println("Format: Q0:w Q1:x Q2:y Q3:z");
    Serial.println("========================================");
    digitalWrite(LED_PIN, HIGH);  // LED on = streaming
  } else {
    Serial.println("ERROR: DMP initialization failed!");
    Serial.println("Make sure ICM_20948_USE_DMP is defined in ICM_20948_C.h");
    while (1) {
      blinkLED(3, 100);
      delay(1000);
    }
  }
}

void loop() {
  // Structure to hold DMP data from FIFO
  icm_20948_DMP_data_t data;
  
  // Read FIFO
  myICM.readDMPdataFromFIFO(&data);
  
  // Check if read was successful
  if ((myICM.status == ICM_20948_Stat_Ok) || (myICM.status == ICM_20948_Stat_FIFOMoreDataAvail)) {
    
    // Check if we have valid Game Rotation Vector (6-axis quaternion) data
    if ((data.header & DMP_header_bitmap_Quat6) > 0) {
      
      // Extract raw quaternion components (Q1, Q2, Q3)
      // Note: DMP Quat6 only provides Q1, Q2, Q3. We compute Q0.
      long q1_raw = data.Quat6.Data.Q1;
      long q2_raw = data.Quat6.Data.Q2;
      long q3_raw = data.Quat6.Data.Q3;
      
      // Convert to double (scale factor: 2^30 = 1073741824.0)
      // This converts from fixed-point to normalized quaternion components
      double q1 = ((double)q1_raw) / 1073741824.0;
      double q2 = ((double)q2_raw) / 1073741824.0;
      double q3 = ((double)q3_raw) / 1073741824.0;
      
      // Compute Q0 (w component) from constraint: Q0^2 + Q1^2 + Q2^2 + Q3^2 = 1
      double q0 = sqrt(1.0 - ((q1 * q1) + (q2 * q2) + (q3 * q3)));
      
      // Send quaternion in the format expected by Python parser
      // Format: "Q0:value Q1:value Q2:value Q3:value"
      Serial.print("Q0:");
      Serial.print(q0, 4);  // 4 decimal places
      Serial.print(" Q1:");
      Serial.print(q1, 4);
      Serial.print(" Q2:");
      Serial.print(q2, 4);
      Serial.print(" Q3:");
      Serial.println(q3, 4);
    }
  }
  
  // Small delay to prevent overwhelming the serial buffer
  // The DMP FIFO can hold multiple samples, so we'll catch up
  delay(1);
}
