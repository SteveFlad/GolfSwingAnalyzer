# Bluetooth Communication Setup

This guide explains how to use the Bluetooth feature for wireless communication with the Golf Swing Analyzer.

## Overview

The Golf Swing Analyzer now supports both USB Serial and Bluetooth communication:
- **USB/Serial**: Direct wired connection via USB cable
- **Bluetooth**: Wireless connection using Bluetooth Classic (SPP - Serial Port Profile)

## Requirements

### Python Side
Install the PyBluez library:
```bash
pip install pybluez
```

**Note for Windows:**
- PyBluez may require Microsoft Visual C++ Build Tools
- Some systems may need admin privileges for Bluetooth operations
- Alternative: Use `bleak` for BLE support (not yet implemented)

**Note for Linux:**
```bash
sudo apt-get install libbluetooth-dev
pip install pybluez
```

**Note for macOS:**
PyBluez has limited support on macOS. Consider using alternative BLE libraries.

### Firmware Side
The ESP32 firmware needs to be compiled with Bluetooth support enabled.

## Firmware Setup

### Option 1: Use the Bluetooth-Enabled Firmware

1. Copy `main_bluetooth.cpp` to replace `main.cpp`:
   ```bash
   cp src/main_bluetooth.cpp src/main.cpp
   ```

2. Build and upload:
   ```bash
   pio run --target upload
   ```

### Option 2: Enable Bluetooth in Existing Firmware

Add Bluetooth Serial to your existing `main.cpp`:

```cpp
#include "BluetoothSerial.h"

BluetoothSerial SerialBT;

void setup() {
    // ... existing setup code ...
    
    // Initialize Bluetooth
    SerialBT.begin("GolfSwingAnalyzer");
    
    // ... rest of setup ...
}

void loop() {
    // ... existing loop code ...
    
    // Send data to both Serial and Bluetooth
    Serial.println(data);
    if (SerialBT.hasClient()) {
        SerialBT.println(data);
    }
}
```

## Usage

### 1. Start the Firmware
Upload and run the firmware on your ESP32. The device will:
- Show up as "GolfSwingAnalyzer" in Bluetooth device lists
- Blink the LED 3 times to indicate Bluetooth started
- Work with both USB Serial and Bluetooth simultaneously

### 2. Pair the Device (First Time Only)

**Windows:**
1. Open Settings → Bluetooth & devices
2. Click "Add device"
3. Select "GolfSwingAnalyzer"
4. Wait for pairing to complete

**Linux:**
```bash
bluetoothctl
scan on
# Wait for device to appear
pair XX:XX:XX:XX:XX:XX
connect XX:XX:XX:XX:XX:XX
```

### 3. Use the GUI

1. Open the Golf Swing Analyzer application
2. Select "Bluetooth" connection type
3. Click "Scan" to discover devices
4. Select "GolfSwingAnalyzer" from the list
5. Click "Connect"

## LED Indicators

- **Solid ON**: Bluetooth initialized, no client connected
- **Blinking**: Bluetooth client connected and data streaming
- **3 Blinks on startup**: Bluetooth successfully started

## Troubleshooting

### "PyBluez library not installed"
```bash
pip install pybluez
```

### "Bluetooth scan failed" on Windows
- Run the application as Administrator
- Ensure Bluetooth is enabled in Windows settings
- Check that the device is not already paired and connected to another application

### "Could not find Bluetooth device"
- Make sure the ESP32 firmware is running
- Check that Bluetooth is enabled on the ESP32 (LED should blink on startup)
- Try increasing scan duration in the code
- Manually pair the device first using OS settings

### Connection drops frequently
- Reduce distance between ESP32 and computer
- Minimize interference from other Bluetooth/WiFi devices
- Check power supply to ESP32 (low power can cause instability)

### Data not received
- Check that both USB Serial and Bluetooth are not fighting for resources
- Monitor via USB Serial first to ensure data is being generated
- Try disconnecting USB Serial when using Bluetooth

## Performance Notes

- **Range**: Typically 10-30 feet depending on environment
- **Latency**: Slightly higher than USB Serial (~20-50ms added)
- **Reliability**: USB Serial is more reliable for development
- **Battery**: Bluetooth allows battery-powered operation

## Switching Between USB and Bluetooth

You can use both simultaneously or switch between them:
- The firmware sends data to both USB Serial and Bluetooth
- The Python application can connect to either
- Choose the appropriate option in the GUI

## Security

The current implementation uses unsecured Bluetooth SPP:
- No PIN required for pairing
- Data is not encrypted
- For production use, consider adding authentication

To add a PIN, modify the firmware:
```cpp
SerialBT.begin("GolfSwingAnalyzer", true);  // true = enable SSP
SerialBT.setPin("1234");  // Set PIN
```
