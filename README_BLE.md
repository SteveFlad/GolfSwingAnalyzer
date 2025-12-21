# BLE Bluetooth Support for Golf Swing Analyzer

## Overview

The Golf Swing Analyzer now supports **BLE (Bluetooth Low Energy)** wireless communication in addition to USB/Serial. This allows you to analyze golf swings without any cables attached to the club.

## What Changed?

### Hardware Support
- **ESP32-S3** natively supports BLE (Bluetooth Low Energy)
- **Note:** ESP32-S3 does NOT support Bluetooth Classic (SPP)
- BLE uses GATT (Generic Attribute Profile) services and characteristics

### Software Changes

#### Python (GUI)
1. **New Module:** `ble_capture.py` - Handles BLE communication using the `bleak` library
2. **Updated:** `main.py` - Now supports both USB/Serial and BLE connections
3. **Requirement:** `bleak>=0.19.0` - Cross-platform BLE library (Windows/macOS/Linux)

#### ESP32 Firmware
1. **New Firmware:** `main.cpp` - Now includes BLE GATT server
2. **BLE Service:** UUID `12345678-1234-1234-1234-123456789abc`
3. **BLE Characteristic:** UUID `87654321-4321-4321-4321-cba987654321`
4. **Device Name:** "GolfSwingAnalyzer"

## Installation

### Install Python BLE Library

```bash
# Activate your virtual environment first
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# Install bleak library
pip install bleak
```

Or install all requirements:
```bash
pip install -r requirements.txt
```

### Flash BLE Firmware

The new firmware with BLE support is already activated. To build and upload:

```bash
# From the GolfSwingAnalyzer project directory
pio run -t upload
```

## Usage

### 1. Start the Application

```bash
python main.py
```

### 2. Select Connection Type

In the GUI, choose:
- **USB/Serial** - For wired connection (traditional)
- **Bluetooth** - For wireless BLE connection (new!)

### 3. Scan for Devices

#### USB/Serial Mode:
1. Click "Scan" to list available COM ports
2. Select your ESP32-S3 port (usually shows as "USB Serial Device")

#### Bluetooth Mode:
1. Make sure your ESP32-S3 is powered on (via USB or battery)
2. Click "Scan" to discover BLE devices
3. Look for "GolfSwingAnalyzer" in the device list
4. Select it and click "Connect"

### 4. Capture Data

Once connected (either USB or BLE):
1. Click "Start Capture" to begin recording quaternion data
2. Perform your golf swing
3. Click "Stop Capture" when done
4. Click "Visualize 3D" to see the club path

## Technical Details

### BLE Architecture

```
[ESP32-S3 Firmware]
    ↓ BLE GATT Server
    ↓ Service: 12345678-1234-1234-1234-123456789abc
    ↓ Characteristic: 87654321-4321-4321-4321-cba987654321
    ↓ Notifications (Quaternion data)
[Python GUI]
    ↓ bleak library (BleakClient)
    ↓ AsyncIO event loop (separate thread)
    ↓ Callback to visualizer
```

### Data Format

Both USB/Serial and BLE send the same quaternion format:
```
Q0:0.9999 Q1:0.0001 Q2:-0.0050 Q3:0.0123
```

### Performance

- **Sample Rate:** ~66 Hz (same as USB/Serial)
- **Latency:** ~20-50ms (slightly higher than USB but acceptable)
- **Range:** ~10-30 meters depending on environment
- **Battery Life:** Depends on power source (USB power bank recommended)

## Troubleshooting

### "BLE Not Available" Error

**Solution:** Install the bleak library:
```bash
pip install bleak
```

### Cannot Find "GolfSwingAnalyzer" Device

**Check:**
1. ESP32-S3 is powered on (LED should be on)
2. Firmware with BLE support is flashed
3. Windows Bluetooth is enabled (Settings → Bluetooth & devices)
4. No other app is connected to the device

**Solution:**
1. Unplug and replug the ESP32-S3 USB cable (power cycle)
2. Remove "GolfSwingAnalyzer" from Windows Bluetooth settings if paired
3. Try scanning again

### Connection Fails or Times Out

**Try:**
1. Move ESP32-S3 closer to your computer
2. Remove any metal obstacles between devices
3. Restart Windows Bluetooth:
   - Settings → Bluetooth & devices → Turn off → Wait 5s → Turn on
4. Power cycle the ESP32-S3

### Data Stream Stops After Connecting

**Check:**
1. Connection monitoring shows "receiving data" status
2. Firmware is running correctly (open Serial Monitor at 115200 baud)
3. Sensor is working (you should see quaternion data in Serial Monitor)

**Solution:**
- If sensor fails, check I2C wiring (SDA=GPIO5, SCL=GPIO6)
- Flash firmware again with `pio run -t upload`

### BLE is Slow or Laggy

**Optimize:**
1. Reduce distance between ESP32-S3 and computer
2. Close other Bluetooth devices/connections
3. Use USB/Serial for critical testing (BLE for demos/convenience)

## Switching Between USB and BLE Firmware

### Current Setup (BLE Enabled)
The active firmware (`src/main.cpp`) supports both USB Serial AND BLE simultaneously. You can:
- View data on Serial Monitor (USB) at 115200 baud
- Connect wirelessly via BLE at the same time

### Reverting to USB-Only

If you want to go back to USB-only firmware:

```bash
cd src
Move-Item -Path "main.cpp" -Destination "main_ble.cpp.bak"
Move-Item -Path "main_usb_only.cpp.bak" -Destination "main.cpp"
pio run -t upload
```

## Advantages of BLE

✅ **Wireless** - No cables during swing  
✅ **Portable** - Use with battery power pack  
✅ **Convenient** - Easy setup for demos  
✅ **Safe** - No USB cable to trip over  

## Disadvantages of BLE

❌ **Slightly slower** - ~20-50ms latency vs instant USB  
❌ **Connection issues** - Environmental interference possible  
❌ **Power required** - Needs battery or USB power bank  
❌ **Limited range** - Works best within 10-20 meters  

## Recommendations

- **Development/Testing:** Use USB/Serial (more reliable, faster debugging)
- **Demos/Presentations:** Use BLE (no cables, cleaner setup)
- **Field Use:** Use BLE with USB battery pack (portable, convenient)
- **Troubleshooting:** Always test USB first before debugging BLE issues

## Future Enhancements

Potential improvements for BLE support:

- [ ] Auto-reconnect on connection loss
- [ ] Battery level monitoring
- [ ] Multiple device support
- [ ] BLE data compression for higher throughput
- [ ] Power-saving sleep modes

## References

- **Bleak Documentation:** https://bleak.readthedocs.io/
- **ESP32 BLE Guide:** https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/bluetooth/esp_gatts.html
- **GATT Specification:** https://www.bluetooth.com/specifications/gatt/

---

**Note:** This implementation is based on the working BLE code from the `XIAO_ESP32S3_COM_test` project, which has been tested and proven to work reliably with the ESP32-S3 hardware.
