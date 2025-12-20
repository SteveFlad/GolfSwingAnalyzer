# ICM-20948 I2C Address Configuration

## The Issue
The ICM-20948 failed to initialize because the firmware is looking for the sensor at the wrong I2C address.

## Understanding AD0 Pin
The **AD0 pin** on the ICM-20948 determines its I2C address:

| AD0 Connection | I2C Address | Firmware Setting |
|----------------|-------------|------------------|
| **GND (Low)**  | 0x68        | `AD0_VAL = 0`   |
| **3.3V (High)**| 0x69        | `AD0_VAL = 1`   |
| **Floating**   | 0x69        | `AD0_VAL = 1`   |

## Quick Diagnosis

### Step 1: Run I2C Scanner
Upload the I2C scanner to see which address your sensor is using:

1. **Temporarily rename files:**
   ```
   src/main.cpp → src/main.cpp.backup
   scan_i2c.cpp → src/main.cpp
   ```

2. **Upload the scanner:**
   - Click PlatformIO Upload button
   - Or run: `pio run --target upload`

3. **View output:**
   - Open Serial Monitor (115200 baud)
   - Or run: `python test_serial.py`

4. **Check results:**
   - If device found at **0x68** → AD0 is LOW (connected to GND)
   - If device found at **0x69** → AD0 is HIGH or floating

### Step 2: Fix the Configuration

**Option A: Hardware Fix (Easier)**
- If sensor is at 0x68, connect AD0 pin to 3.3V or leave it floating
- This makes it work with current firmware (`AD0_VAL = 1`)

**Option B: Firmware Fix**
- If sensor is at 0x68 and you want to keep it there
- Change line 27 in `src/main.cpp`:
  ```cpp
  #define AD0_VAL 0  // Changed from 1 to 0
  ```
- Re-upload the firmware

### Step 3: Restore and Upload
1. **Restore original firmware:**
   ```
   src/main.cpp → scan_i2c.cpp.backup
   src/main.cpp.backup → src/main.cpp
   ```

2. **Upload the fixed firmware**

## Common ICM-20948 Breakout Boards

- **SparkFun ICM-20948**: AD0 has pullup to 3.3V by default (works with `AD0_VAL = 1`)
- **DFRobot ICM-20948**: Usually has AD0 connected to GND (needs `AD0_VAL = 0`)
- **Generic boards**: Check schematic or use I2C scanner

## Wiring Double-Check

Verify your connections:
```
ICM-20948    →    XIAO ESP32S3
---------          ------------
VCC/3V3      →    3.3V
GND          →    GND
SDA          →    GPIO 5 (D4)
SCL          →    GPIO 6 (D5)
AD0          →    3.3V, GND, or floating
```

## Still Not Working?

If the I2C scanner finds **no devices**:
1. Check all wire connections
2. Verify 3.3V power is reaching the sensor
3. Try different I2C pullup resistors (typically 4.7kΩ on SDA and SCL)
4. Test with a multimeter that there's continuity in your wires
