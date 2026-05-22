"""
Reset Calibration to Default State
Run this to fix corrupted calibration before recalibrating
"""

import json
import time

calibration_file = 'calibration_data.json'

# Create fresh calibration with identity matrix (no transformation)
fresh_calibration = {
    "rotation_matrix": [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0]
    ],
    "axis_signs": [1, 1, 1],
    "gravity_reference": [0.0, 0.0, 9.81],
    "is_calibrated": False,  # Mark as not calibrated
    "timestamp": time.time()
}

# Save to file
with open(calibration_file, 'w') as f:
    json.dump(fresh_calibration, f, indent=2)

print("=" * 70)
print("CALIBRATION RESET COMPLETE")
print("=" * 70)
print(f"\nReset {calibration_file} to default state (identity matrix)")
print("\nNext steps:")
print("1. Run main.py")
print("2. Click 'Calibrate Sensor' button")
print("3. Follow the calibration wizard carefully:")
print("   - Hold each position steady for 2-3 seconds")
print("   - Ensure sensor is properly connected during calibration")
print("   - Complete all 4 positions (address, toe up, toe down, face up)")
print("\n" + "=" * 70)
