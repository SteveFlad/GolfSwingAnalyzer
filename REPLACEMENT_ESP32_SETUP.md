# ESP32-S3 Replacement Setup Guide

## Current System Status (2026-07-11)

**Defective Board:** XIAO ESP32S3 (MAC: B8:F8:62:FC:53:D4)
- ✅ USB Serial: Working perfectly on COM3
- ❌ BLE Radio: Hardware defect (advertises but connections fail)

## What You Need

1. **Replacement Board:** XIAO ESP32S3 (or compatible ESP32-S3 with BLE)
2. **IMU Sensor:** GY-ICM20948V2 (already working, just reconnect)
3. **Wiring:** Same as current setup
   - SDA → GPIO5 (D4)
   - SCL → GPIO6 (D5)
   - VCC → 3.3V
   - GND → GND

## Firmware Upload Steps

### 1. Connect New ESP32-S3
```bash
# Check which COM port it appears on
python check_esp32_port.py
```

### 2. Update platformio.ini if needed
If new board uses different COM port, edit:
```ini
upload_port = COM#    ; Change to your port
monitor_port = COM#
```

### 3. Upload Firmware
```bash
.\quick_upload.bat
```

Expected output:
```
✓ RAM:   13.6% (44476 bytes)
✓ Flash: 28.0% (936137 bytes)  
✓ SUCCESS
```

### 4. Test USB Serial First
```bash
python test_serial.py
```
Should see quaternion data:
```
Q0:0.9894 Q1:0.092 Q2:0.019 Q3:0.1104
```

### 5. Test BLE
```bash
python test_ble_scan.py
```
Should see:
```
• GolfSwingAnalyzer
  Address: XX:XX:XX:XX:XX:XX  (will be different)
  Signal: Strong 📶
```

### 6. Test Full Connection
```bash
python test_esp32_ble_simple.py
```
Should complete successfully with:
```
✓ Connected
✓ Found X services
✓ BLE hardware appears to be working!
```

## If BLE Still Fails on Replacement

1. **Pair in Windows Settings:**
   - Settings → Bluetooth & devices → Add device
   - Select "GolfSwingAnalyzer"

2. **Disable Bluetooth Power Saving:**
   - Device Manager → Bluetooth adapter → Properties
   - Power Management → Uncheck "turn off to save power"

3. **Check USB cable:** Some cables are power-only (no data)

## Current Working Files

All firmware and Python code is ready:
- `src/main.cpp` - Latest firmware with BLE + USB Serial
- `ble_capture.py` - Enhanced with 30s timeout, debugging
- `serial_capture.py` - USB fallback (confirmed working)
- `main.py` - GUI with both connection modes

## Calibration Data

Your sensor calibration in `calibration_data.json` will work with any ESP32 as long as you mount the IMU in the same physical position/orientation on the club.

## Troubleshooting New Board

**Problem:** Firmware won't upload
```bash
# Hold BOOT button while connecting USB
# Or manually set port in platformio.ini
```

**Problem:** I2C sensor not detected
```bash
# Upload test firmware to verify wiring
pio run -e seeed_xiao_esp32s3 -t upload -e test_firmware/main_i2c_scan.cpp
```

**Problem:** BLE works but data is wrong
```bash
# Recalibrate sensor (old calibration may not match new mounting)
python main.py
# → Click "Calibrate Sensor" button
```

## Contact Info

Firmware created: 2026-07-11
- Firmware size: 936KB flash, 44KB RAM
- BLE Service UUID: 12345678-1234-1234-1234-123456789abc
- BLE Characteristic: 87654321-4321-4321-4321-cba987654321
- Data format: "Q0:w Q1:x Q2:y Q3:z" at ~66Hz
