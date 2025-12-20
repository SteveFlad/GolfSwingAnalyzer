# Golf Swing Analyzer - ESP32 Firmware

This folder contains the PlatformIO firmware for the XIAO ESP32S3 microcontroller that captures data from the ICM-20948 sensor.

## Hardware Setup

### Components
- **Board**: Seeed XIAO ESP32S3
- **Sensor**: ICM-20948 9-DOF IMU (via I2C)

### Wiring
Connect the ICM-20948 to the XIAO ESP32S3:
- **VCC** → 3.3V
- **GND** → GND
- **SDA** → GPIO5 (XIAO ESP32S3 default SDA)
- **SCL** → GPIO6 (XIAO ESP32S3 default SCL)

### I2C Address
The firmware tries AD0=1 (0x69) by default. If your sensor uses AD0=0 (0x68), change `AD0_VAL` in `src/main.cpp`:
```cpp
#define AD0_VAL 0  // Change to 0 if AD0 pin is grounded
```

## Building and Uploading

### Using PlatformIO CLI
```bash
# Build the project
pio run

# Upload to the board
pio run --target upload

# Monitor serial output
pio device monitor
```

### Using VS Code
1. Open the project folder in VS Code
2. Make sure PlatformIO extension is installed
3. Use the PlatformIO toolbar at the bottom:
   - ✓ (checkmark) to build
   - → (arrow) to upload
   - 🔌 (plug) to start serial monitor

## Usage

1. **Upload the firmware** to your XIAO ESP32S3
2. **Connect the ICM-20948** sensor via I2C
3. **Open serial monitor** at 115200 baud
4. The firmware will:
   - Initialize the ICM-20948
   - Enable the DMP (Digital Motion Processor)
   - Stream quaternion data in format: `Q0:w Q1:x Q2:y Q3:z`

5. **Run the Python application** (in parent directory):
   ```bash
   python main.py
   ```
6. Select the COM port in the GUI and start capturing!

## Troubleshooting

### Sensor not found
- Check I2C wiring (SDA=GPIO5, SCL=GPIO6)
- Verify 3.3V power supply
- Try changing `AD0_VAL` in the code

### No quaternion data
- Make sure the SparkFun library DMP feature is enabled
- Check that `ICM_20948_USE_DMP` is defined in the library

### Slow data rate
- The DMP output rate is set to maximum (~225Hz)
- Adjust `setDMPODRrate()` parameter in setup() if needed

## Data Format

The firmware outputs quaternion data in this format:
```
Q0:0.9990 Q1:-0.0123 Q2:0.0456 Q3:-0.0078
```

Where:
- **Q0** (w): Scalar component
- **Q1** (x): X-axis rotation
- **Q2** (y): Y-axis rotation  
- **Q3** (z): Z-axis rotation

This format is automatically parsed by the Python application's `serial_capture.py` module.
