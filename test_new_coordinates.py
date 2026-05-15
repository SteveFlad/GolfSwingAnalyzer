"""Quick test of new natural golf coordinate system"""
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

# Calculate positions with NEW natural golf coordinate mapping
all_positions = []
for d in data:
    quat_xyzw = [d['q1'], d['q2'], d['q3'], d['q0']]
    club_vector = rotate_vector_by_quaternion(quat_xyzw, [0, 0, club_length_m])
    
    # NEW mapping: Sensor Y→Golf X (target), Sensor Z→Golf Y (in/out), Sensor X→Golf Z (height)
    golf_pos = np.array([club_vector[1], club_vector[2], club_vector[0]])
    all_positions.append(golf_pos)

all_positions = np.array(all_positions)

print("="*70)
print("NATURAL GOLF COORDINATE SYSTEM TEST")
print("="*70)
print("\nCoordinate mapping:")
print("  X = Target Line (left-right, should be small)")
print("  Y = In/Out (back-through, should be large)")
print("  Z = Height (up-down, should be moderate)")
print()

x_range = np.ptp(all_positions[:, 0]) * m_to_ft
y_range = np.ptp(all_positions[:, 1]) * m_to_ft
z_range = np.ptp(all_positions[:, 2]) * m_to_ft

print(f"X (Target Line):  {x_range:.2f} ft  {'✓ GOOD' if x_range < 3 else '✗ Too much'}")
print(f"Y (In/Out):       {y_range:.2f} ft  {'✓ GOOD' if 6 <= y_range <= 9 else '✗ Outside ideal'}")
print(f"Z (Height):       {z_range:.2f} ft  {'✓ GOOD' if 4 <= z_range <= 7 else '✗ Outside ideal'}")

print("\n" + "="*70)
print("EXPECTED for good golf swing:")
print("  X: 1-2 ft (club stays near ball)")
print("  Y: 6-8 ft (backswing and follow-through arc)")
print("  Z: 4-6 ft (club rises in backswing)")
print("="*70)
