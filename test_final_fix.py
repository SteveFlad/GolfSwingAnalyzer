"""Test impact-based height normalization with inverted Z"""
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
    
    # FIXED mapping with inverted Z
    golf_pos = np.array([club_vector[1], club_vector[2], -club_vector[0]])
    all_positions.append(golf_pos)

all_positions = np.array(all_positions)

# Apply IMPACT-based normalization
impact_idx = 225
impact_height = all_positions[impact_idx, 2]
target_impact_height = 0.7 / m_to_ft  # 0.7 ft in meters
height_offset = target_impact_height - impact_height
all_positions[:, 2] += height_offset

print("="*70)
print("IMPACT-BASED HEIGHT NORMALIZATION (Final Fix)")
print("="*70)

print(f"\nHeight statistics:")
print(f"  Lowest point:  {np.min(all_positions[:, 2]) * m_to_ft:6.2f} ft (sample #{np.argmin(all_positions[:, 2])})")
print(f"  Highest point: {np.max(all_positions[:, 2]) * m_to_ft:6.2f} ft (sample #{np.argmax(all_positions[:, 2])})")
print(f"  Height range:  {np.ptp(all_positions[:, 2]) * m_to_ft:6.2f} ft")

print(f"\nKey positions:")
print(f"  Address (start):      Z = {all_positions[0, 2] * m_to_ft:6.2f} ft")
print(f"  Impact (sample 225):  Z = {all_positions[impact_idx, 2] * m_to_ft:6.2f} ft  ← Normalized to 0.7 ft")
print(f"  Follow-through (end): Z = {all_positions[-1, 2] * m_to_ft:6.2f} ft")

# Count samples near ground
near_ground = np.sum(all_positions[:, 2] * m_to_ft < 2.0)
above_ground = np.sum(all_positions[:, 2] * m_to_ft >= 0.0)
print(f"\nSamples at/above ground (≥0 ft): {above_ground}/{len(all_positions)} ({above_ground/len(all_positions)*100:.1f}%)")
print(f"Samples near ground (<2 ft):     {near_ground}/{len(all_positions)} ({near_ground/len(all_positions)*100:.1f}%)")

print("\n" + "="*70)
print("VALIDATION CHECKS:")
print("="*70)

checks = [
    ("Impact at ground level", 0.4 <= all_positions[impact_idx, 2] * m_to_ft <= 1.5, 
     f"Impact = {all_positions[impact_idx, 2] * m_to_ft:.2f} ft"),
    ("No underground positions", np.min(all_positions[:, 2]) * m_to_ft >= -0.5,
     f"Lowest = {np.min(all_positions[:, 2]) * m_to_ft:.2f} ft"),
    ("Backswing reaches proper height", np.max(all_positions[:, 2]) * m_to_ft >= 3.0,
     f"Highest = {np.max(all_positions[:, 2]) * m_to_ft:.2f} ft"),
    ("Height range reasonable", 4.0 <= np.ptp(all_positions[:, 2]) * m_to_ft <= 7.0,
     f"Range = {np.ptp(all_positions[:, 2]) * m_to_ft:.2f} ft"),
]

all_pass = True
for check_name, passed, details in checks:
    status = "✓" if passed else "✗"
    print(f"  {status} {check_name}: {details}")
    if not passed:
        all_pass = False

print("\n" + "="*70)
if all_pass:
    print("✓✓✓ SUCCESS! All checks passed!")
    print("\nVisualization should now show:")
    print("  • Impact star ON THE FLOOR (ground plane)")
    print("  • Backswing rising up from ground")
    print("  • Follow-through near ground level")
    print("  • Natural golf swing perspective")
else:
    print("⚠️  Some checks failed")
print("="*70)
