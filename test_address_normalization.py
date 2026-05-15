"""Test address-based height normalization"""
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

# Calculate positions
all_positions = []
for d in data:
    quat_xyzw = [d['q1'], d['q2'], d['q3'], d['q0']]
    club_vector = rotate_vector_by_quaternion(quat_xyzw, [0, 0, club_length_m])
    golf_pos = np.array([club_vector[1], club_vector[2], club_vector[0]])
    all_positions.append(golf_pos)

all_positions = np.array(all_positions)

# Apply address-based normalization (same as new visualizer.py)
address_height = all_positions[0, 2]
target_address_height = 0.5 / m_to_ft  # 0.5 ft in meters
height_offset = target_address_height - address_height
all_positions[:, 2] += height_offset

impact_idx = 225

print("="*70)
print("ADDRESS-BASED HEIGHT NORMALIZATION")
print("="*70)

print(f"\nHeight statistics:")
print(f"  Lowest point:  {np.min(all_positions[:, 2]) * m_to_ft:6.2f} ft")
print(f"  Highest point: {np.max(all_positions[:, 2]) * m_to_ft:6.2f} ft")
print(f"  Height range:  {np.ptp(all_positions[:, 2]) * m_to_ft:6.2f} ft")

print(f"\nKey positions:")
print(f"  Address (start):      Z = {all_positions[0, 2] * m_to_ft:6.2f} ft  ← Should be ~0.5 ft")
print(f"  Impact (sample 225):  Z = {all_positions[impact_idx, 2] * m_to_ft:6.2f} ft  ← Should be ~0.5-1 ft")
print(f"  Follow-through (end): Z = {all_positions[-1, 2] * m_to_ft:6.2f} ft")

print("\n" + "="*70)
if 0.3 <= all_positions[impact_idx, 2] * m_to_ft <= 2.0:
    print("✓ SUCCESS: Impact is now near ground level!")
    print("  Ball contact zone for driver: 0.5-1.5 ft")
else:
    print(f"⚠️  Impact at {all_positions[impact_idx, 2] * m_to_ft:.2f} ft - still seems off")
print("="*70)

print(f"\nFull impact position:")
print(f"  X (Target Line): {all_positions[impact_idx, 0] * m_to_ft:6.2f} ft")
print(f"  Y (In/Out):      {all_positions[impact_idx, 1] * m_to_ft:6.2f} ft")  
print(f"  Z (Height):      {all_positions[impact_idx, 2] * m_to_ft:6.2f} ft")

print(f"\nNow impact should appear on the FLOOR (X-Y plane),")
print(f"not on the wall!")
