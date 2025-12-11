# Golf Swing Analyzer

A Python-based GUI application for capturing, analyzing, and visualizing golf club swing data using the ICM-20948 IMU sensor attached to an ESP32.

## Features

- **Real-time Data Capture**: Connect to ESP32 via serial port and capture quaternion orientation data
- **3D Visualization**: View the club head path in 3D space with multiple perspectives
- **Speed Analysis**: Track and display club head speed throughout the swing
- **Face Direction**: Visualize club face orientation at all points in the swing
- **Data Management**: Save and load swing data for later analysis
- **Interactive GUI**: Easy-to-use interface for controlling capture and visualization

## Hardware Requirements

- ESP32 development board (e.g., ESP32-WROOM-32)
- ICM-20948 9-axis IMU sensor
- USB cable for serial connection
- Mount to attach sensor to golf club head

## Software Requirements

- Python 3.7 or higher
- PlatformIO (for ESP32 firmware)

## Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Flash the ESP32 firmware:**
   - Open the companion PlatformIO project `Quant_ICM20948_to_ESP32WROOM32`
   - Connect your ESP32 via USB
   - Build and upload the firmware

## Usage

### Starting the Application

```bash
python main.py
```

### Capturing a Swing

1. **Connect to ESP32:**
   - Select your COM port from the dropdown
   - Click "Connect"
   - Wait for "Status: Connected" to appear

2. **Capture Data:**
   - Mount the sensor on your golf club head
   - Click "Start Capture"
   - Perform your golf swing
   - Click "Stop Capture"

3. **Save Your Data:**
   - Click "Save Data"
   - Choose a filename (data will be saved in JSON format)

### Viewing 3D Visualization

1. After capturing or loading data, click "Visualize 3D"
2. The visualization shows:
   - **3D Trajectory**: Full path with color-coded speed (green=slow, red=fast)
   - **Speed Graph**: Club head angular velocity over time
   - **Top View**: X-Y plane perspective
   - **Side View**: X-Z plane perspective
   - **Red Arrows**: Club face direction indicators

### Loading Previous Data

1. Click "Load Data"
2. Select a previously saved JSON file
3. Click "Visualize 3D" to view the swing

## Project Structure

```
GolfSwingAnalyzer/
├── main.py                 # Main GUI application
├── serial_capture.py       # Serial communication module
├── visualizer.py           # 3D visualization module
├── requirements.txt        # Python dependencies
├── README.md              # This file
└── data/                  # Directory for saved swing data
```

## Data Format

Swing data is saved in JSON format with the following structure:

```json
{
  "timestamp": "2025-12-11T10:30:00",
  "data_points": 150,
  "data": [
    {
      "q0": 0.707,
      "q1": 0.0,
      "q2": 0.707,
      "q3": 0.0,
      "timestamp": 1702295400.123,
      "raw": "Q0:0.707 Q1:0.000 Q2:0.707 Q3:0.000"
    },
    ...
  ]
}
```

## Understanding the Visualization

### Quaternion Data (Q0, Q1, Q2, Q3)
The ICM-20948 outputs orientation as quaternions, which represent 3D rotations:
- **Q0** (w): Scalar component
- **Q1** (x): X-axis component
- **Q2** (y): Y-axis component  
- **Q3** (z): Z-axis component

### Speed Calculation
Angular speed is calculated from the rotation rate between consecutive measurements. Higher speeds appear in red/yellow, while slower movements appear in green.

### Face Direction
Red arrows indicate the direction the club face is pointing at various points in the swing.

## Troubleshooting

### "No serial port found"
- Ensure ESP32 is connected via USB
- Check that USB drivers are installed
- Try clicking "Refresh" to update the port list

### "Failed to connect"
- Verify the correct COM port is selected
- Ensure no other program is using the serial port
- Check that ESP32 firmware is running correctly

### Visualization not appearing
- Ensure you have captured or loaded data
- Check that matplotlib is properly installed
- Try closing and reopening the visualization

## Future Enhancements

- Integration with accelerometer data for true positional tracking
- Comparison of multiple swings
- Export to video format
- Advanced analytics (swing plane, tempo, etc.)
- Real-time 3D visualization during capture

## License

MIT License - feel free to modify and use for your projects

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Acknowledgments

- SparkFun for the ICM-20948 Arduino library
- PlatformIO for the ESP32 development platform
