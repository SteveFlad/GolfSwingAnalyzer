"""Test the height normalization to verify impact is near ground"""
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

# Calculate positions with natural golf coordinates
all_positions = []
for d in data:
    quat_xyzw = [d['q1'], d['q2'], d['q3'], d['q0']]
    club_vector = rotate_vector_by_quaternion(quat_xyzw, [0, 0, club_length_m])
    
    # NEW mapping: Sensor Y→Golf X (target), Sensor Z→Golf Y (in/out), Sensor X→Golf Z (height)
    golf_pos = np.array([club_vector[1], club_vector[2], club_vector[0]])
    all_positions.append(golf_pos)

all_positions = np.array(all_positions)

# Apply height normalization (same as visualizer.py)
min_height = np.min(all_positions[:, 2])
all_positions[:, 2] -= min_height

# Impact is at sample 225
impact_idx = 225

print("="*70)
print("HEIGHT NORMALIZATION TEST")
print("="*70)

print(f"\nAfter normalizing to ground level:")
print(f"\nLowest point:  {np.min(all_positions[:, 2]) * m_to_ft:6.2f} ft (sample #{np.argmin(all_positions[:, 2])})")
print(f"Highest point: {np.max(all_positions[:, 2]) * m_to_ft:6.2f} ft (sample #{np.argmax(all_positions[:, 2])})")
print(f"Height range:  {np.ptp(all_positions[:, 2]) * m_to_ft:6.2f} ft")

print(f"\nKey positions:")
print(f"  Address (start):      Z = {all_positions[0, 2] * m_to_ft:6.2f} ft")
print(f"  Impact (sample 225):  Z = {all_positions[impact_idx, 2] * m_to_ft:6.2f} ft")
print(f"  Follow-through (end): Z = {all_positions[-1, 2] * m_to_ft:6.2f} ft")

print("\n" + "="*70)
if all_positions[impact_idx, 2] * m_to_ft < 1.0:
    print("✓ SUCCESS: Impact is now near ground level!")
else:
    print("⚠️  Impact still too high")
print("="*70)

# Show full position at impact
print(f"\nFull impact position:")
print(f"  X (Target Line): {all_positions[impact_idx, 0] * m_to_ft:6.2f} ft")
print(f"  Y (In/Out):      {all_positions[impact_idx, 1] * m_to_ft:6.2f} ft")
print(f"  Z (Height):      {all_positions[impact_idx, 2] * m_to_ft:6.2f} ft")
