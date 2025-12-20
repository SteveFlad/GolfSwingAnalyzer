# Troubleshooting: No Data from XIAO ESP32S3

## Problem
No data is being received from the XIAO ESP32S3 on the serial port (COM10).

## Step-by-Step Troubleshooting

### Step 1: Test Basic Serial Communication

First, let's verify that serial communication works at all.

1. **Rename the main file temporarily:**
   ```
   In VS Code, rename: src/main.cpp → src/main_icm.cpp
   Rename: src/main_test_basic.cpp → src/main.cpp
   ```

2. **Upload the basic test firmware:**
   ```
   Click the PlatformIO Upload button or run:
   platformio run --target upload
   ```

3. **Open serial monitor:**
   ```
   platformio device monitor --port COM10 --baud 115200
   ```

4. **Expected output:**
   You should see:
   ```
   ========================================
   XIAO ESP32S3 - Basic Serial Test
   ========================================
   If you can see this, serial is working!
   
   Counter: 0
   Uptime (ms): 1000
   
   Counter: 1
   Uptime (ms): 2000
   ...
   ```

5. **Results:**
   - ✅ **If you see output:** Serial is working! Go to Step 2.
   - ❌ **If no output:**
     - Try pressing the RESET button on the XIAO
     - Try unplugging and replugging the USB cable
     - Make sure you're using the correct COM port
     - Try a different USB cable (some cables are power-only)
     - Check if Windows recognizes the device in Device Manager

---

### Step 2: Test I2C and Sensor Detection

Now let's check if the sensor is connected and detected.

1. **Rename files:**
   ```
   src/main.cpp → src/main_test_basic.cpp
   src/main_i2c_scan.cpp → src/main.cpp
   ```

2. **Upload the I2C scanner:**
   ```
   platformio run --target upload
   ```

3. **Open serial monitor and check output**

4. **Expected output if sensor is connected:**
   ```
   ========================================
   I2C Scanner - XIAO ESP32S3
   ========================================
   SDA: GPIO5 (D4)
   SCL: GPIO6 (D5)
   ========================================
   
   Scanning for I2C devices...
   I2C device found at address 0x68 !
     -> Likely ICM-20948 or MPU-6050
   
   Found 1 device(s)
   ========================================
   ```

5. **Results:**
   - ✅ **If device found at 0x68 or 0x69:** Great! Sensor is connected. Go to Step 3.
   - ❌ **If no devices found:**
     - Check wiring:
       - GY-ICM20948V2 VCC → XIAO 3V3
       - GY-ICM20948V2 GND → XIAO GND
       - GY-ICM20948V2 SDA → XIAO GPIO5 (D4 pin)
       - GY-ICM20948V2 SCL → XIAO GPIO6 (D5 pin)
     - Make sure the sensor board has power (some have a power LED)
     - Try using external pull-up resistors (4.7kΩ) on SDA and SCL lines
     - Make sure you have the correct sensor board (GY-ICM20948V2)

---

### Step 3: Test Full ICM-20948 Firmware

Now restore the original firmware and test.

1. **Rename files back:**
   ```
   src/main.cpp → src/main_i2c_scan.cpp
   src/main_icm.cpp → src/main.cpp
   ```

2. **Upload the original firmware:**
   ```
   platformio run --target upload
   ```

3. **Open serial monitor**

4. **Expected output:**
   ```
   ========================================
   Golf Swing Analyzer - ESP32 Firmware
   Board: XIAO ESP32S3
   Sensor: ICM-20948
   ========================================
   Initializing ICM-20948...
   Trying address 0x69 (AD0=HIGH/floating)...
     Attempt 1: All ok
   ========================================
   ICM-20948 initialized successfully at 0x69
   ========================================
   Initializing DMP...
   ========================================
   DMP ENABLED! Streaming quaternions...
   Format: Q0:w Q1:x Q2:y Q3:z
   ========================================
   Q0:1.0000 Q1:0.0000 Q2:0.0000 Q3:0.0000
   Q0:0.9999 Q1:0.0001 Q2:-0.0002 Q3:0.0001
   ...
   ```

5. **Common Issues:**

   **A. "Failed to initialize ICM-20948"**
   - Go back to Step 2 to verify I2C connection
   - Try connecting the AD0 pin to GND or 3.3V explicitly

   **B. "DMP initialization failed"**
   - This is a library issue. The SparkFun library sometimes has DMP problems.
   - Solution: Try this alternative library:
     ```
     In platformio.ini, replace the lib_deps line with:
     lib_deps = 
         https://github.com/finani/ICM20948_DMP_Arduino.git
     ```

   **C. Serial output shows initialization but no quaternion data**
   - DMP may not be outputting data
   - Try resetting the device
   - Check if you need to enable specific DMP features in the library

---

## Quick Command Reference

**Upload firmware:**
```powershell
C:\Users\sjfla\.platformio\penv\Scripts\platformio.exe run --target upload
```

**Open serial monitor:**
```powershell
C:\Users\sjfla\.platformio\penv\Scripts\platformio.exe device monitor --port COM10 --baud 115200
```

**Test with Python:**
```powershell
python test_serial.py COM10
```

**Run main application:**
```powershell
python main.py
```

---

## Hardware Checklist

- [ ] XIAO ESP32S3 connected via USB
- [ ] Correct COM port identified (COM10)
- [ ] GY-ICM20948V2 sensor board has power
- [ ] Wiring connections are secure:
  - VCC → 3V3
  - GND → GND  
  - SDA → GPIO5 (D4)
  - SCL → GPIO6 (D5)
- [ ] USB cable supports data (not just power)
- [ ] Firmware uploaded successfully
- [ ] Device can be seen in Windows Device Manager

---

## Still Having Issues?

1. **Check the PlatformIO build output** - look for any compilation errors
2. **Try a different USB port** on your computer
3. **Update the XIAO ESP32S3 bootloader** (check Seeed documentation)
4. **Test with a simple Arduino blink sketch** to verify the board works
5. **Check the SparkFun ICM-20948 library issues** on GitHub for known problems

---

## Alternative: Use Different Library

If the SparkFun library isn't working, you can try an alternative approach with the Adafruit ICM20X library (doesn't use DMP, but reads raw sensor data):

```ini
lib_deps = 
    adafruit/Adafruit ICM20X @ ^2.0.0
    adafruit/Adafruit BusIO @ ^1.14.0
```

This will require modifying the firmware code to use raw sensor readings instead of DMP quaternions.
