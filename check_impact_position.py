"""Check the actual 3D position at impact to diagnose the issue"""
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

# Impact is at sample 225 (from find_impact.py)
impact_idx = 225

print("="*70)
print("IMPACT POSITION ANALYSIS")
print("="*70)

print(f"\nImpact occurs at sample #{impact_idx}")
print(f"\nPosition at impact (meters):")
print(f"  X (Target Line): {all_positions[impact_idx, 0]:7.3f} m  ({all_positions[impact_idx, 0] * m_to_ft:6.2f} ft)")
print(f"  Y (In/Out):      {all_positions[impact_idx, 1]:7.3f} m  ({all_positions[impact_idx, 1] * m_to_ft:6.2f} ft)")
print(f"  Z (Height):      {all_positions[impact_idx, 2]:7.3f} m  ({all_positions[impact_idx, 2] * m_to_ft:6.2f} ft)")

print(f"\n⚠️  PROBLEM: Impact height is {all_positions[impact_idx, 2] * m_to_ft:.2f} ft")
print("   In reality, golf ball sits ~0.1-0.2 ft off ground on a tee")
print("   Club head at impact should be near ground level!")

print("\n" + "="*70)
print("FULL SWING HEIGHT ANALYSIS")
print("="*70)

min_height = np.min(all_positions[:, 2])
max_height = np.max(all_positions[:, 2])

print(f"\nLowest point:  {min_height * m_to_ft:6.2f} ft (sample #{np.argmin(all_positions[:, 2])})")
print(f"Highest point: {max_height * m_to_ft:6.2f} ft (sample #{np.argmax(all_positions[:, 2])})")
print(f"Height range:  {(max_height - min_height) * m_to_ft:6.2f} ft")

print(f"\nAddress position (start): Z = {all_positions[0, 2] * m_to_ft:6.2f} ft")
print(f"Impact position:          Z = {all_positions[impact_idx, 2] * m_to_ft:6.2f} ft")
print(f"Follow-through (end):     Z = {all_positions[-1, 2] * m_to_ft:6.2f} ft")

print("\n" + "="*70)
print("ISSUE IDENTIFIED:")
print("="*70)
print("\nThe problem: We're calculating ABSOLUTE club head position in space,")
print("but treating the grip as if it's at origin (0,0,0).")
print("\nIn reality:")
print("  • Your hands/grip are ~3-4 feet off the ground at address")
print("  • Club head hangs DOWN from grip by ~46 inches (3.8 ft)")
print("  • So club head at address should be near ground level")
print("\nThe quaternion shows club ORIENTATION, not grip position.")
print("We need to:")
print("  1. Set a reference grip position (e.g., 3.5 ft height)")
print("  2. Calculate where club head hangs relative to that grip")
print("="*70)
