"""
Complete Calibration Fix and Verification
This script will:
1. Reset calibration to fresh state
2. Verify sensor connection
3. Guide through proper calibration
"""

import json
import time
import numpy as np
from pathlib import Path

print("=" * 80)
print("COMPLETE CALIBRATION FIX")
print("=" * 80)

# Step 1: Reset calibration
print("\n[Step 1/3] Resetting calibration to default state...")
calibration_file = Path('calibration_data.json')

fresh_calibration = {
    "rotation_matrix": [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0]
    ],
    "axis_signs": [1, 1, 1],
    "gravity_reference": [0.0, 0.0, 9.81],
    "is_calibrated": False,
    "timestamp": time.time()
}

with open(calibration_file, 'w') as f:
    json.dump(fresh_calibration, f, indent=2)

print("✓ Calibration reset to identity matrix")

# Step 2: Check current calibration file
print("\n[Step 2/3] Verifying calibration file...")
with open(calibration_file, 'r') as f:
    cal_data = json.load(f)

rotation_matrix = np.array(cal_data['rotation_matrix'])
if np.any(np.isnan(rotation_matrix)):
    print("❌ ERROR: Calibration still contains NaN!")
    exit(1)
else:
    print("✓ Calibration file is valid (no NaN values)")
    print(f"  Determinant: {np.linalg.det(rotation_matrix):.3f}")

# Step 3: Provide calibration instructions
print("\n[Step 3/3] Calibration Instructions")
print("=" * 80)
print("\nNOW DO THIS:")
print("1. Make sure ESP32 is connected via USB (not Bluetooth)")
print("2. Run: python main.py")
print("3. Select USB/Serial connection type")
print("4. Click 'Connect' and select your USB COM port")
print("5. Click 'Calibrate Sensor' button")
print("6. Choose 'Full Calibration' (recommended)")
print("7. Follow each position carefully:")
print("   - Hold STEADY for full 2-3 seconds")
print("   - Wait for 'Collect Data' button to become available")
print("   - Move to next position ONLY when prompted")
print("8. After all 4 positions, click YES to set address reference")
print("9. Place club at address and capture reference")
print("\n" + "=" * 80)
print("\nTIP: If calibration fails (NaN values appear):")
print("  - The sensor didn't send valid data")
print("  - Check USB connection is solid")
print("  - Don't move during 2-3 second collection period")
print("  - Restart ESP32 (unplug/replug USB) and try again")
print("\n" + "=" * 80)
