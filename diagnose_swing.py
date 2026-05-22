"""
Diagnostic script to check swing data and calibration
"""

import json
import numpy as np
from pathlib import Path

print("=" * 70)
print("SWING DATA DIAGNOSTIC")
print("=" * 70)

# Check if swing data file exists
data_file = Path('data/ClubHeadData.json')
if not data_file.exists():
    print("\n❌ ERROR: No swing data file found at data/ClubHeadData.json")
    print("   Take a new swing to create data file.")
    exit(1)

# Load swing data
try:
    with open(data_file, 'r') as f:
        swing_data = json.load(f)
    print(f"\n✓ Swing data file loaded successfully")
    print(f"  Timestamp: {swing_data.get('timestamp', 'N/A')}")
    print(f"  Data points: {swing_data.get('data_points', len(swing_data.get('data', [])))}")
except Exception as e:
    print(f"\n❌ ERROR loading swing data: {e}")
    exit(1)

# Check quaternion data validity
data = swing_data.get('data', [])
if not data:
    print("\n❌ ERROR: No quaternion data in file")
    exit(1)

print(f"\n✓ Found {len(data)} quaternion samples")

# Check for NaN or invalid quaternions
invalid_count = 0
for i, point in enumerate(data[:10]):  # Check first 10
    q = [point.get('q0'), point.get('q1'), point.get('q2'), point.get('q3')]
    if any(x is None or np.isnan(x) for x in q):
        invalid_count += 1
        print(f"  ❌ Sample {i}: Invalid quaternion {q}")
    elif i < 3:
        print(f"  ✓ Sample {i}: q=[{q[0]:.4f}, {q[1]:.4f}, {q[2]:.4f}, {q[3]:.4f}]")

if invalid_count > 0:
    print(f"\n❌ ERROR: Found {invalid_count} invalid quaternions in first 10 samples")
else:
    print("\n✓ All checked quaternion samples are valid")

# Check calibration
print("\n" + "=" * 70)
print("CALIBRATION CHECK")
print("=" * 70)

cal_file = Path('calibration_data.json')
if not cal_file.exists():
    print("\n❌ No calibration file found")
    exit(1)

try:
    with open(cal_file, 'r') as f:
        cal_data = json.load(f)
    print("\n✓ Calibration file loaded")
except Exception as e:
    print(f"\n❌ ERROR loading calibration: {e}")
    exit(1)

# Check rotation matrix
rotation_matrix = cal_data.get('rotation_matrix', [])
has_nan = False
try:
    rotation_array = np.array(rotation_matrix)
    has_nan = np.any(np.isnan(rotation_array))
    if has_nan:
        print("\n❌ PROBLEM FOUND: Rotation matrix contains NaN values!")
        print(f"  Matrix: {rotation_matrix}")
        print("\n  This will cause visualization to fail.")
        print("\n  SOLUTION: Run 'python reset_calibration.py' then recalibrate")
    else:
        print("\n✓ Rotation matrix is valid (no NaN values)")
        print(f"  Determinant: {np.linalg.det(rotation_array):.3f}")
except Exception as e:
    print(f"\n❌ ERROR checking rotation matrix: {e}")
    has_nan = True

# Check address reference
has_address = cal_data.get('has_address_reference', False)
if has_address:
    address_quat = cal_data.get('address_quaternion', [])
    if any(np.isnan(x) for x in address_quat):
        print("\n❌ Address quaternion contains NaN values")
    else:
        print(f"\n✓ Address reference set: face angle = {cal_data.get('address_face_angle', 0):.1f}°")
else:
    print("\n⚠ No address reference set (visualization will use raw coordinates)")

# Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

if has_nan:
    print("\n❌ CALIBRATION IS CORRUPTED")
    print("\nSteps to fix:")
    print("1. Run: python reset_calibration.py")
    print("2. Run: python main.py")
    print("3. Connect to sensor")
    print("4. Click 'Calibrate Sensor' and follow wizard carefully")
    print("5. Take a new swing")
else:
    print("\n✓ Calibration appears valid")
    print("\nYou can:")
    print("1. Run: python find_impact.py  (to analyze current swing)")
    print("2. Run: python main.py  (to visualize with 'Analyze Swing')")
    
print("\n" + "=" * 70)
