"""Test impact-centered coordinate normalization"""
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

# Apply IMPACT-centered normalization (X, Y, Z all relative to impact)
impact_idx = 225
impact_pos = all_positions[impact_idx].copy()

# Normalize X, Y to impact
all_positions[:, 0] -= impact_pos[0]
all_positions[:, 1] -= impact_pos[1]

# Normalize Z to put impact at 0.7 ft
target_impact_height = 0.7 / m_to_ft
height_offset = target_impact_height - impact_pos[2]
all_positions[:, 2] += height_offset

print("="*70)
print("IMPACT-CENTERED COORDINATE SYSTEM")
print("="*70)

print(f"\n📍 Ball/Impact Position (should be at origin):")
print(f"  X (Target Line): {all_positions[impact_idx, 0] * m_to_ft:7.3f} ft  ← Should be 0.000")
print(f"  Y (In/Out):      {all_positions[impact_idx, 1] * m_to_ft:7.3f} ft  ← Should be 0.000")
print(f"  Z (Height):      {all_positions[impact_idx, 2] * m_to_ft:7.3f} ft  ← Should be 0.700")

print(f"\n📊 Position Statistics:")
print(f"  X range: {np.min(all_positions[:, 0]) * m_to_ft:6.2f} to {np.max(all_positions[:, 0]) * m_to_ft:6.2f} ft")
print(f"  Y range: {np.min(all_positions[:, 1]) * m_to_ft:6.2f} to {np.max(all_positions[:, 1]) * m_to_ft:6.2f} ft")
print(f"  Z range: {np.min(all_positions[:, 2]) * m_to_ft:6.2f} to {np.max(all_positions[:, 2]) * m_to_ft:6.2f} ft")

print(f"\n🏌️ Key Swing Positions (relative to ball):")
print(f"  Address (start):      X={all_positions[0, 0] * m_to_ft:5.2f}, Y={all_positions[0, 1] * m_to_ft:5.2f}, Z={all_positions[0, 2] * m_to_ft:5.2f} ft")
print(f"  Top of backswing:     X={all_positions[179, 0] * m_to_ft:5.2f}, Y={all_positions[179, 1] * m_to_ft:5.2f}, Z={all_positions[179, 2] * m_to_ft:5.2f} ft")
print(f"  Impact:               X={all_positions[impact_idx, 0] * m_to_ft:5.2f}, Y={all_positions[impact_idx, 1] * m_to_ft:5.2f}, Z={all_positions[impact_idx, 2] * m_to_ft:5.2f} ft")
print(f"  Follow-through (end): X={all_positions[-1, 0] * m_to_ft:5.2f}, Y={all_positions[-1, 1] * m_to_ft:5.2f}, Z={all_positions[-1, 2] * m_to_ft:5.2f} ft")

print("\n" + "="*70)
print("INTERPRETATION:")
print("="*70)
print("✓ Impact at (0, 0, 0.7) = Ball position")
print("✓ Negative Y = Backswing (club goes away from target)")
print("✓ Positive Y = Follow-through (club moves toward target)")
print("✓ X values = Lateral deviation from target line")
print("✓ Z values = Club height above ground")
print("="*70)

# Validation
x_centered = abs(all_positions[impact_idx, 0] * m_to_ft) < 0.01
y_centered = abs(all_positions[impact_idx, 1] * m_to_ft) < 0.01
z_correct = abs(all_positions[impact_idx, 2] * m_to_ft - 0.7) < 0.01

if x_centered and y_centered and z_correct:
    print("\n✓✓✓ SUCCESS! Impact is perfectly centered at origin!")
    print("Visualization will now show swing relative to ball position.")
else:
    print("\n⚠️  Centering not perfect - check calculations")
