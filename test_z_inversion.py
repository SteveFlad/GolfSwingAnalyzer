"""Test Z-axis inversion fix"""
import json
import numpy as np
from scipy.spatial.transform import Rotation as R

def rotate_vector_by_quaternion(quat_xyzw, vector):
    """Rotate a vector by a quaternion (scipy format: x,y,z,w)"""
    rot = R.from_quat(quat_xyzw)
    return rot.apply(vector)

# Load swing data
with open('data/ClubHeadData.json', 'r') as f:
    swing_data = json.load(f)

data = swing_data['data']
club_length_m = 1.168
m_to_ft = 3.28084

# Calculate positions with INVERTED Z-axis
all_positions = []
for d in data:
    quat_xyzw = [d['q1'], d['q2'], d['q3'], d['q0']]
    club_vector = rotate_vector_by_quaternion(quat_xyzw, [0, 0, club_length_m])
    
    # FIXED mapping with inverted Z: Sensor Y→Golf X, Sensor Z→Golf Y, -Sensor X→Golf Z
    golf_pos = np.array([club_vector[1], club_vector[2], -club_vector[0]])
    all_positions.append(golf_pos)

all_positions = np.array(all_positions)

# Apply address-based normalization
address_height = all_positions[0, 2]
target_address_height = 0.5 / m_to_ft  # 0.5 ft in meters
height_offset = target_address_height - address_height
all_positions[:, 2] += height_offset

impact_idx = 225

print("="*70)
print("Z-AXIS INVERSION FIX TEST")
print("="*70)

print(f"\nHeight statistics (Z-axis now pointing UP):")
print(f"  Lowest point:  {np.min(all_positions[:, 2]) * m_to_ft:6.2f} ft (sample #{np.argmin(all_positions[:, 2])})")
print(f"  Highest point: {np.max(all_positions[:, 2]) * m_to_ft:6.2f} ft (sample #{np.argmax(all_positions[:, 2])})")
print(f"  Height range:  {np.ptp(all_positions[:, 2]) * m_to_ft:6.2f} ft")

print(f"\nKey positions:")
print(f"  Address (start):      Z = {all_positions[0, 2] * m_to_ft:6.2f} ft")
print(f"  Impact (sample 225):  Z = {all_positions[impact_idx, 2] * m_to_ft:6.2f} ft")
print(f"  Follow-through (end): Z = {all_positions[-1, 2] * m_to_ft:6.2f} ft")

# Check which samples are near ground (< 2 ft)
near_ground = np.sum(all_positions[:, 2] * m_to_ft < 2.0)
print(f"\nSamples near ground (<2 ft): {near_ground}/{len(all_positions)}")

print("\n" + "="*70)
print("EXPECTED BEHAVIOR:")
print("="*70)
print("✓ Address should be ~0.5 ft (ball on tee)")
print("✓ Impact should be ~0.5-1.5 ft (near ground)")
print("✓ Highest point should be 4-6 ft (top of backswing)")
print("✓ Lowest point should be ~0 ft (at or near ground)")
print()

# Validate
checks = []
checks.append(("Address height", 0.3 <= all_positions[0, 2] * m_to_ft <= 1.5))
checks.append(("Impact height", 0.3 <= all_positions[impact_idx, 2] * m_to_ft <= 2.0))
checks.append(("Lowest point at ground", np.min(all_positions[:, 2]) * m_to_ft >= -0.5))
checks.append(("Highest in range", 3.0 <= np.max(all_positions[:, 2]) * m_to_ft <= 7.0))

print("Validation:")
all_pass = True
for check_name, passed in checks:
    status = "✓" if passed else "✗"
    print(f"  {status} {check_name}")
    if not passed:
        all_pass = False

print("\n" + "="*70)
if all_pass:
    print("✓✓✓ SUCCESS! Orientation is now correct!")
    print("Impact should now appear on the FLOOR (ground plane)")
else:
    print("Some checks failed - may need further adjustment")
print("="*70)
