"""
Accurate Golf Metrics from Quaternion Data
Shows what CAN be reliably measured without position tracking
"""

import json
import numpy as np
from scipy.spatial.transform import Rotation as R

# Load swing data
with open('data/ClubHeadData.json', 'r') as f:
    data = json.load(f)['data']

print("=" * 70)
print("RELIABLE GOLF SWING METRICS")
print("=" * 70)

# Find impact (max speed)
speeds = []
club_length = 1.168  # meters

for i in range(1, len(data)):
    q_prev = [data[i-1]['q0'], data[i-1]['q1'], data[i-1]['q2'], data[i-1]['q3']]
    q_curr = [data[i]['q0'], data[i]['q1'], data[i]['q2'], data[i]['q3']]
    
    # Angular change
    dot = sum(p*c for p, c in zip(q_prev, q_curr))
    angle_rad = 2 * np.arccos(min(abs(dot), 1.0))
    
    # Angular velocity (assume 100Hz)
    angular_vel = angle_rad * 100  # rad/s
    linear_vel_mph = angular_vel * club_length * 2.23694
    speeds.append(linear_vel_mph)

speeds = np.array(speeds)
impact_idx = np.argmax(speeds)
impact_speed = speeds[impact_idx]

print(f"\n✓ CLUB HEAD SPEED AT IMPACT: {impact_speed:.1f} mph")
print(f"  Sample #{impact_idx + 1} of {len(data)}")

# Get impact quaternion
impact_quat = [data[impact_idx]['q0'], data[impact_idx]['q1'], 
               data[impact_idx]['q2'], data[impact_idx]['q3']]

# Convert to rotation matrix
q_scipy = [impact_quat[1], impact_quat[2], impact_quat[3], impact_quat[0]]
rot = R.from_quat(q_scipy)

# Face normal (assume Z-axis in sensor frame)
face_normal = rot.apply([0, 0, 1])

# Project to horizontal plane and calculate angle
face_angle = np.degrees(np.arctan2(face_normal[1], face_normal[0]))

print(f"\n✓ FACE ANGLE AT IMPACT: {face_angle:.1f}°")
print("  (relative to sensor mounting)")

# Shaft lean (up/down tilt)
shaft_vector = rot.apply([-1, 0, 0])  # Shaft along -X
shaft_tilt = np.degrees(np.arcsin(shaft_vector[2]))

print(f"\n✓ SHAFT LEAN AT IMPACT: {shaft_tilt:.1f}°")
print("  (negative = forward lean, positive = back)")

# Get address quaternion
address_quat = [data[0]['q0'], data[0]['q1'], data[0]['q2'], data[0]['q3']]
q_addr = [address_quat[1], address_quat[2], address_quat[3], address_quat[0]]
rot_addr = R.from_quat(q_addr)

# Calculate rotation from address to impact
relative_rot = rot * rot_addr.inv()
axis_angle = relative_rot.as_rotvec()
total_rotation = np.degrees(np.linalg.norm(axis_angle))

print(f"\n✓ TOTAL ROTATION (Address → Impact): {total_rotation:.1f}°")

# Swing tempo
total_time = len(data) * 0.01  # seconds
backswing_time = impact_idx * 0.01

print(f"\n✓ SWING TIMING:")
print(f"  Total time: {total_time:.2f} sec")
print(f"  Time to impact: {backswing_time:.2f} sec")

print("\n" + "=" * 70)
print("WHAT'S NOT RELIABLE:")
print("=" * 70)
print("\n❌ 3D POSITION TRAJECTORY")
print("  Cannot calculate true club head path without:")
print("  - Double integration of accelerometer data, or")
print("  - External motion capture system")
print("\n  The visualizer's 3D path assumes grip stays at origin,")
print("  which creates fictitious trajectories.")

print("\n" + "=" * 70)
print("RECOMMENDATION:")
print("=" * 70)
print("\nFocus on these reliable metrics:")
print("  1. Club head speed at impact")
print("  2. Face angle at impact (after calibration)")
print("  3. Shaft lean/attack angle")
print("  4. Swing timing and tempo")
print("\nFor accurate 3D tracking, you would need:")
print("  - Camera-based motion capture (e.g., launch monitor)")
print("  - GPS/UWB position tracking")
print("  - Or mount sensors at grip + club head")

print("\n" + "=" * 70)
