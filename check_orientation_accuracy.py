"""
Check if club orientation at impact matches address orientation
This validates whether the club head actually returned to the ball
"""

import json
import numpy as np
from scipy.spatial.transform import Rotation as R

def quaternion_angle_difference(q1, q2):
    """Calculate the angle difference between two quaternions in degrees"""
    # Convert from [w,x,y,z] to [x,y,z,w] for scipy
    q1_scipy = [q1[1], q1[2], q1[3], q1[0]]
    q2_scipy = [q2[1], q2[2], q2[3], q2[0]]
    
    r1 = R.from_quat(q1_scipy)
    r2 = R.from_quat(q2_scipy)
    
    # Compute relative rotation
    r_diff = r1.inv() * r2
    
    # Get angle of rotation
    angle = r_diff.magnitude()
    return np.degrees(angle)

# Load data
with open('data/ClubHeadData.json', 'r') as f:
    data = json.load(f)

swing_data = data['data']

print(f"Total samples: {len(swing_data)}")

# Find address (first 20% of data, lowest speed)
search_end = len(swing_data) // 5
speeds = []
for i in range(min(search_end, len(swing_data)-1)):
    if i == 0:
        speeds.append(0)
    else:
        # Simple speed calculation
        q1 = [swing_data[i-1]['q0'], swing_data[i-1]['q1'], swing_data[i-1]['q2'], swing_data[i-1]['q3']]
        q2 = [swing_data[i]['q0'], swing_data[i]['q1'], swing_data[i]['q2'], swing_data[i]['q3']]
        angle_diff = quaternion_angle_difference(q1, q2)
        speeds.append(angle_diff)

address_idx = np.argmin(speeds)
print(f"\nAddress detected at sample #{address_idx}")

# Find impact (maximum speed)
all_speeds = []
for i in range(len(swing_data)-1):
    q1 = [swing_data[i]['q0'], swing_data[i]['q1'], swing_data[i]['q2'], swing_data[i]['q3']]
    q2 = [swing_data[i+1]['q0'], swing_data[i+1]['q1'], swing_data[i+1]['q2'], swing_data[i+1]['q3']]
    angle_diff = quaternion_angle_difference(q1, q2)
    all_speeds.append(angle_diff)

impact_idx = np.argmax(all_speeds)
print(f"Impact detected at sample #{impact_idx}")

# Get quaternions
address_quat = [swing_data[address_idx]['q0'], swing_data[address_idx]['q1'], 
                swing_data[address_idx]['q2'], swing_data[address_idx]['q3']]
impact_quat = [swing_data[impact_idx]['q0'], swing_data[impact_idx]['q1'], 
               swing_data[impact_idx]['q2'], swing_data[impact_idx]['q3']]

print(f"\nAddress quaternion: q0={address_quat[0]:.4f}, q1={address_quat[1]:.4f}, q2={address_quat[2]:.4f}, q3={address_quat[3]:.4f}")
print(f"Impact quaternion:  q0={impact_quat[0]:.4f}, q1={impact_quat[1]:.4f}, q2={impact_quat[2]:.4f}, q3={impact_quat[3]:.4f}")

# Calculate orientation difference
orientation_diff = quaternion_angle_difference(address_quat, impact_quat)
print(f"\n🎯 Orientation difference between address and impact: {orientation_diff:.2f}°")

if orientation_diff < 5:
    print("✅ EXCELLENT: Club returned to nearly identical orientation!")
elif orientation_diff < 15:
    print("✅ GOOD: Club orientation is very close to address")
elif orientation_diff < 30:
    print("⚠️  MODERATE: Some orientation change from address to impact")
else:
    print("❌ LARGE DIFFERENCE: Club orientation significantly different at impact")

# Calculate what the position should be based on orientation
# If orientation is the same, position should be the same (relative to grip)
print(f"\n💡 Key Insight:")
print(f"   If orientation difference is small ({orientation_diff:.2f}°), the club head")
print(f"   is in the same position RELATIVE TO THE GRIP at address and impact.")
print(f"   The calculated position difference of 2.6 feet is an artifact of assuming")
print(f"   the grip stays at origin, which is wrong - the grip moves forward during swing.")

# Additional analysis: compare face normals
def get_face_normal(quat):
    """Get club face normal direction from quaternion"""
    # Face normal in sensor frame (Z-axis)
    face_sensor = [0, 0, 1]
    q_scipy = [quat[1], quat[2], quat[3], quat[0]]
    rot = R.from_quat(q_scipy)
    return rot.apply(face_sensor)

address_face = get_face_normal(address_quat)
impact_face = get_face_normal(impact_quat)

print(f"\nFace Normal Directions:")
print(f"   Address: [{address_face[0]:+.3f}, {address_face[1]:+.3f}, {address_face[2]:+.3f}]")
print(f"   Impact:  [{impact_face[0]:+.3f}, {impact_face[1]:+.3f}, {impact_face[2]:+.3f}]")

face_angle_diff = np.degrees(np.arccos(np.clip(np.dot(address_face, impact_face), -1, 1)))
print(f"   Face angle difference: {face_angle_diff:.2f}°")
