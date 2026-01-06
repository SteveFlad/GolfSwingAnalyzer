# Sensor Calibration Guide

## Overview

The ICM-20948 sensor can be mounted on a golf club head in various orientations. The calibration feature maps the sensor's X, Y, Z axes to the club's natural coordinate system, ensuring accurate motion tracking regardless of how the sensor is physically mounted.

## Why Calibration is Important

Without calibration:
- Sensor axes may not align with the club's natural movement directions
- Data visualization may show incorrect swing paths
- Analysis results may be misleading

With calibration:
- Sensor data is automatically transformed to the club's coordinate system
- Consistent results regardless of mounting orientation
- Accurate 3D swing visualization

## Club Coordinate System

The calibration maps sensor axes to the following club frame:

- **X-axis**: Along the shaft (positive toward grip)
- **Y-axis**: Toe-heel direction (positive toward toe)
- **Z-axis**: Face normal (positive toward target)

## Calibration Methods

### Method 1: Full Calibration (Recommended)

This method provides the most accurate orientation mapping by collecting data from four distinct club positions.

**Time required**: ~2 minutes  
**Accuracy**: Highest

#### Steps:

1. **Connect to Device**
   - Connect your sensor via USB or Bluetooth
   - Ensure data is being received (check status display)

2. **Start Calibration**
   - Click "Calibrate Sensor" button
   - Click "Start Calibration" in the wizard

3. **Position 1: Address**
   - Place club in normal address position
   - Club head on ground (or hovering just above)
   - Shaft at normal address angle (~60-70°)
   - Face square to target
   - Click "Collect Data"
   - Hold steady for 2 seconds while collecting

4. **Position 2: Toe Up**
   - Hold club horizontally
   - Rotate so TOE points straight up to sky
   - Heel points down to ground
   - Face perpendicular to ground
   - Click "Collect Data"
   - Hold steady for 2 seconds

5. **Position 3: Toe Down**
   - Hold club horizontally
   - Rotate so TOE points straight down to ground
   - Heel points up to sky
   - Face perpendicular to ground
   - Click "Collect Data"
   - Hold steady for 2 seconds

6. **Position 4: Face Up**
   - Lay club on its back
   - Face pointing straight up to sky
   - Grip and head at same height (horizontal)
   - Click "Collect Data"
   - Hold steady for 2 seconds

7. **Complete**
   - Wait for processing
   - Calibration is saved automatically

### Method 2: Simple Calibration (Quick)

This method uses only gravity alignment and is faster but less accurate.

**Time required**: ~30 seconds  
**Accuracy**: Basic

#### Steps:

1. **Connect to Device**
   - Connect your sensor via USB or Bluetooth

2. **Start Simple Calibration**
   - Click "Calibrate Sensor" button
   - Click "Simple Calibration" in the wizard

3. **Address Position**
   - Place club in normal address position
   - Club head on ground or hovering
   - Shaft at normal address angle
   - Face square to target
   - Click "Collect"
   - Hold steady for 2 seconds

4. **Complete**
   - Wait for processing
   - Calibration is saved automatically

## Tips for Best Results

### Mounting Considerations
- Mount sensor securely to club head
- Avoid mounting near heavy magnets or electronics
- Ensure sensor won't shift during swings

### During Calibration
- Hold club as steady as possible during collection
- Avoid touching or bumping the club
- Keep sensor away from metal objects or electronic devices
- Make sure club is not resting on metal surfaces
- If a position fails, simply restart calibration

### Environmental Factors
- Calibrate in a stable environment (not in a moving vehicle)
- Avoid strong magnetic fields
- Temperature should be stable

## Using Calibrated Data

Once calibrated:

1. **Automatic Application**
   - All captured data is automatically transformed
   - No manual intervention needed
   - Works with both USB and Bluetooth connections

2. **Verification**
   - Check "Status: Calibrated" in the Calibration section
   - Saved data includes both raw and calibrated values
   - Visualizations use calibrated data

3. **Re-calibration**
   - Re-calibrate if sensor is remounted
   - Re-calibrate if data seems incorrect
   - No need to re-calibrate between sessions if mount hasn't changed

## Resetting Calibration

To reset calibration to default (uncalibrated):

1. Click "Reset Calibration" button
2. Confirm the reset
3. System reverts to identity transformation (no axis remapping)

## Troubleshooting

### "Not enough samples collected"
- **Cause**: Device not sending data or connection lost
- **Solution**: 
  - Check device connection
  - Verify data is appearing in status display
  - Try reconnecting and starting calibration again

### "Calibration failed"
- **Cause**: Invalid or inconsistent data
- **Solution**:
  - Ensure club was held steady during collection
  - Check for magnetic interference
  - Make sure positions were distinct (don't use same position twice)
  - Try calibration again

### "Device not connected" error
- **Cause**: Trying to calibrate without connection
- **Solution**: Connect to device first via USB or Bluetooth

### Rotation matrix determinant warning
- **Cause**: Collected positions were too similar or co-linear
- **Solution**:
  - Ensure each position is distinctly different
  - Hold positions more carefully
  - Use Simple Calibration if Full Calibration keeps failing

## Technical Details

### Calibration Algorithm

**Full Calibration**:
1. Collects accelerometer data in 4 positions
2. Identifies gravity vectors for each position
3. Constructs orthogonal basis vectors for club frame
4. Builds rotation matrix to transform sensor → club frame
5. Validates with face-up position

**Simple Calibration**:
1. Collects accelerometer data in address position
2. Identifies primary gravity-aligned axis
3. Constructs basic rotation matrix for axis swapping
4. Less accurate but faster

### Calibration Data Storage

- Stored in: `calibration_data.json`
- Contains:
  - 3×3 rotation matrix
  - Axis sign multipliers
  - Gravity reference vector
  - Timestamp
- Persists between sessions
- Automatically loaded on startup

### Data Transformation

Applied to each data point:
```
accel_club = R^T * (accel_sensor * signs)
gyro_club = R^T * (gyro_sensor * signs)
```

Where:
- R = rotation matrix from calibration
- signs = axis sign multipliers
- ^T = matrix transpose

## Firmware Support

The ESP32 firmware supports calibration through:

**Calibration Mode**:
- Triggered by `CAL_START` command
- Sends raw sensor data instead of quaternions
- Format: `RAW AX:x.xx AY:y.yy AZ:z.zz GX:x.xx GY:y.yy GZ:z.zz`
- Exit with `CAL_STOP` command

**Commands** (sent via serial or BLE):
- `CAL_START` - Enable calibration mode
- `CAL_STOP` - Disable calibration mode (resume quaternion output)

## FAQ

**Q: Do I need to calibrate every time I use the device?**  
A: No, calibration is saved and persists between sessions. Only re-calibrate if you remount the sensor.

**Q: Can I calibrate with Bluetooth connection?**  
A: Yes, calibration works with both USB and Bluetooth connections.

**Q: How accurate is the calibration?**  
A: Full calibration typically achieves < 5° accuracy. Simple calibration is less accurate but sufficient for basic use.

**Q: What if my sensor is mounted at an odd angle?**  
A: That's exactly what calibration handles! Any mounting orientation can be calibrated.

**Q: Does calibration affect the quaternion data?**  
A: The calibration currently transforms raw accelerometer and gyroscope data. Quaternion transformation requires additional processing (future enhancement).

**Q: Can I calibrate offline (with saved data)?**  
A: No, calibration requires live sensor data from the device.

## Future Enhancements

Planned improvements:
- Quaternion transformation support
- Magnetometer calibration for absolute heading
- Gyroscope bias calibration
- Multi-point calibration for sensor drift compensation
- Calibration quality metrics and validation
- Export/import calibration profiles

## Support

If you encounter issues:
1. Check the main troubleshooting guides (TROUBLESHOOTING_*.md)
2. Verify sensor is working correctly (test raw data first)
3. Try Simple Calibration if Full Calibration fails
4. Check for environmental interference
5. Ensure firmware is up to date

---

**Version**: 1.0  
**Last Updated**: January 2026
