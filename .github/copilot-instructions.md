# Golf Swing Analyzer - AI Agent Instructions

## Project Overview

**Dual-platform system**: ESP32 firmware (C++/Arduino) + Python GUI for capturing and analyzing golf swings using ICM-20948 IMU sensor with real-time quaternion streaming.

**Data Flow**: ESP32 → (USB/BLE) → Python → Calibration → Quaternion Integration → 3D Visualization

## Architecture

### Firmware (`src/main.cpp`)
- **Board**: XIAO ESP32S3 with ICM-20948 on I2C (SDA=GPIO5, SCL=GPIO6)
- **Outputs**: Madgwick-filtered quaternions (w,x,y,z) at 100Hz over USB Serial (115200 baud) + BLE GATT
- **Format**: `Q0:1.0000 Q1:0.0000 Q2:0.0000 Q3:0.0000` (space-separated)
- **BLE UUIDs**: Service `12345678-1234-1234-1234-123456789abc`, Characteristic `87654321-4321-4321-4321-cba987654321`
- **Calibration**: Firmware responds to `CAL_START`/`CAL_STOP` commands via BLE writes

### Python Application (`main.py`)
- **GUI Framework**: tkinter with maximized window (`root.state('zoomed')`)
- **Three capture modes**: `serial_capture.py` (USB), `ble_capture.py` (BLE), optional Classic Bluetooth
- **Connection pattern**: Set `self.connection_type` ('serial'/'bluetooth'), create capture object, start monitor thread
- **Data structure**: List of dicts with keys `['q0','q1','q2','q3','timestamp']`

### Calibration System (`sensor_calibration.py` + `calibration_wizard.py`)
- **Two-stage transform**: 3x3 rotation matrix + axis sign flips stored in `calibration_data.json`
- **Collection**: Wizard captures 4 static positions (address, toe-up, toe-down, face-up) using accelerometer gravity vectors
- **Application**: `apply_calibration(quaternion)` transforms all quaternions before visualization
- **Critical**: Calibration required for arbitrary sensor mounting angles; auto-loads on startup

### Visualization (`visualizer.py`)
- **Input**: Calibrated quaternion list
- **Processing**: Quaternion differencing → rotation vectors → integrated 3D trajectory
- **Outputs**: 4-panel matplotlib figure (3D path, speed graph, top view, side view)
- **Color mapping**: Speed-based trajectory coloring (green→yellow→red via viridis)

## Key Workflows

### Building & Flashing Firmware
```bash
pio run -e seeed_xiao_esp32s3 -t upload    # Flash ESP32
pio device monitor                         # View serial output
```
- **Dependencies**: Adafruit ICM20X, BusIO, Unified Sensor (auto-installed via platformio.ini)
- **Upload issues**: Check port detection; manually set `upload_port = COM10` if needed

### Running Python Application
```bash
pip install -r requirements.txt
python main.py
```
- **First-time setup**: Run "Calibrate Sensor" wizard before capturing swings
- **BLE requirement**: `bleak` package (Windows 10+ / macOS / Linux BlueZ)

### Testing & Debugging
- **Firmware diagnostics**: Use `test_firmware/main_i2c_scan.cpp` to verify I2C sensor detection
- **Python serial test**: `python test_serial.py` for raw quaternion validation
- **Calibration validation**: `python test_calibration_raw.py` compares raw vs calibrated output

## Critical Conventions

### Quaternion Order
- **Firmware outputs**: `Q0=w, Q1=x, Q2=y, Q3=z` (scalar-first)
- **SciPy convention**: `[x,y,z,w]` (scalar-last) → **always convert** with `[q1,q2,q3,q0]`

### File Persistence
- **Swing data**: `data/ClubHeadData.json` (JSON array of quaternion dicts)
- **Calibration**: `calibration_data.json` in project root (rotation matrix + signs + timestamp)
- **Never**: Hardcode COM ports or device addresses

### Data Format Examples

**Swing Data JSON** (`data/ClubHeadData.json`):
```json
{
  "timestamp": "2025-12-20T19:08:23.206174",
  "data_points": 413,
  "data": [
    {"q0": 0.9894, "q1": 0.092, "q2": 0.019, "q3": 0.1104},
    {"q0": 0.9899, "q1": 0.0854, "q2": 0.0254, "q3": 0.1098}
  ]
}
```

**Calibration JSON** (`calibration_data.json`):
```json
{
  "rotation_matrix": [[1,0,0], [0,1,0], [0,0,1]],
  "axis_signs": [1, -1, 1],
  "gravity_reference": [0, 0, 9.81],
  "is_calibrated": true,
  "timestamp": 1703521234.567
}
```

### Madgwick Filter Tuning
- **Beta parameter** (`src/main.cpp`): `float beta = 0.5f` controls filter responsiveness
- **Lower values** (0.1-0.3): Smoother output, slower convergence, more lag
- **Higher values** (0.5-1.0): Faster response, more noise, quicker adaptation
- **Default 0.5**: Balanced for golf swing dynamics (fast movements with pauses)
- **When to adjust**: Increase for faster swings; decrease if jittery visualization

### Error Handling Pattern
```python
try:
    # operation
except Exception as e:
    self.log_status(f"Error: {str(e)}")
    messagebox.showerror("Title", str(e))
```
- **UI updates**: Always use `self.log_status()` to append to main status text widget
- **Threading**: Capture runs in `monitor_thread`; use `self.monitoring` flag to control loops

### Multi-Connection Support
- **Check availability**: Test `BLEAK_AVAILABLE` before enabling BLE UI elements
- **Fallback gracefully**: Disable Bluetooth radio button if `bleak` import fails
- **State isolation**: Only one active capture object at a time; clean up previous before switching

## Documentation Map

- **README.md**: User guide with calibration quickstart
- **QUICKSTART_CALIBRATION.md**: Step-by-step wizard instructions
- **TROUBLESHOOTING_*.md**: Platform-specific connection issues (I2C, Serial, Bluetooth)
- **CALIBRATION_*.md**: Theory and implementation details
- **README_FIRMWARE.md**: Hardware setup and pinout diagrams

## Common Pitfalls

1. **Quaternion math**: Always normalize after applying calibration rotations
2. **Thread safety**: Don't update tkinter widgets from monitor thread; use `root.after()`
3. **BLE characteristic format**: Pack data as UTF-8 string, not binary (firmware sends ASCII)
4. **PlatformIO paths**: Use `$PROJECT_PACKAGES_DIR` in build_flags, not absolute paths
5. **Calibration loss**: Wizard doesn't auto-connect; must be connected first via main UI

## When Editing

- **Firmware changes**: Rebuild/upload required; test with `pio device monitor` first
- **Python capture modules**: Update both serial and BLE to maintain feature parity
- **Calibration algorithms**: Validate with `test_calibration_raw.py` before committing
- **UI additions**: Follow existing ttk themed widgets; maintain window maximize behavior
