# Windows Bluetooth Quick Start Guide

## Good News!

**No external libraries needed!** The Golf Swing Analyzer now uses Windows native Bluetooth support, which means you don't need to install PyBluez or any other Bluetooth libraries.

## Requirements

- **Windows 10/11** with Bluetooth
- **Python 3.9+**
- **ESP32 with Bluetooth firmware** running

That's it! No pip installs required for Bluetooth.

## Setup Steps

### 1. Upload Bluetooth Firmware to ESP32

The firmware needs to have Bluetooth enabled. Use the `main_bluetooth.cpp` file:

```bash
# In PlatformIO
cp src/main_bluetooth.cpp src/main.cpp
pio run --target upload
```

The firmware will advertise itself as "GolfSwingAnalyzer"

### 2. Pair the Device in Windows

**Important:** You must pair the device in Windows BEFORE using the application.

1. Power on your ESP32 (wait for 3 LED blinks indicating Bluetooth started)
2. Open **Settings** → **Bluetooth & devices**
3. Click **"Add device"** → **"Bluetooth"**
4. Wait for **"GolfSwingAnalyzer"** to appear
5. Click on it to pair (no PIN required)
6. Wait for "Connected" status

### 3. Use the Golf Swing Analyzer App

1. Run the application: `python main.py`
2. You should see: `"Bluetooth support enabled (Windows Native)"`
3. Select **"Bluetooth"** radio button
4. Click **"Scan"** button
5. Select **"GolfSwingAnalyzer"** from the dropdown
6. Click **"Connect"**

## Troubleshooting

### "No paired devices found"
- Make sure you paired the device in Windows Settings first
- The device must show as "Connected" or "Paired" in Settings
- Try removing and re-pairing the device

### "Connection refused" or "Connection timeout"
- Verify the ESP32 is running the Bluetooth firmware
- Check that the ESP32 LED blinked 3 times on startup (Bluetooth initialized)
- Make sure the device isn't already connected to another application
- Try disconnecting other Bluetooth devices
- Restart the ESP32

### "Bluetooth support not available"
- Make sure you're running on Windows 10/11
- Update Python to 3.9 or newer
- Check that Bluetooth is enabled in Windows

### Connection drops or data stops
- Reduce distance between PC and ESP32 (stay within 10-30 feet)
- Check ESP32 power supply (use a good USB cable/power source)
- Minimize WiFi/Bluetooth interference
- Try reconnecting via USB first to verify data is being generated

## Testing Connection

You can test the Bluetooth connection separately:

```bash
python bluetooth_capture_windows.py
```

This will list all paired Bluetooth devices.

## LED Status Indicators

On the ESP32:
- **3 blinks on startup**: Bluetooth successfully initialized
- **Solid ON**: Bluetooth ready, no client connected  
- **Blinking**: Data is being sent to Bluetooth client

## Why Windows Native Works

Python 3.9+ on Windows includes Bluetooth socket support in the standard `socket` module:
- `socket.AF_BLUETOOTH` - Bluetooth address family
- `socket.BTPROTO_RFCOMM` - RFCOMM protocol (Serial Port Profile)

No external dependencies needed!

## Switching Between USB and Bluetooth

The firmware sends data to both USB Serial and Bluetooth simultaneously, so you can:
- Connect via USB for debugging while Bluetooth is paired
- Switch between USB and Bluetooth in the application without changing firmware
- Use USB to verify data is flowing if Bluetooth has issues

## Performance

- **Range**: 10-30 feet (typical)
- **Latency**: ~20-50ms additional vs USB
- **Reliability**: USB is more reliable for consistent data
- **Battery**: Bluetooth allows wireless, battery-powered operation

## Next Steps

Once connected:
1. Click **"Start Capture"** to begin recording
2. Perform your golf swing
3. Click **"Stop Capture"** when done
4. Click **"Visualize 3D"** to see the trajectory

Enjoy wireless golf swing analysis! 🏌️
