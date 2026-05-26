"""
Find the point where club orientation is closest to address orientation
This should be the true impact point (when club returns to ball)
"""

import json
import numpy as np
from scipy.spatial.transform import Rotation as R
import matplotlib.pyplot as plt

def quaternion_angle_difference(q1, q2):
    """Calculate the angle difference between two quaternions in degrees"""
    q1_scipy = [q1[1], q1[2], q1[3], q1[0]]
    q2_scipy = [q2[1], q2[2], q2[3], q2[0]]
    
    r1 = R.from_quat(q1_scipy)
    r2 = R.from_quat(q2_scipy)
    
    r_diff = r1.inv() * r2
    angle = r_diff.magnitude()
    return np.degrees(angle)

# Load data
with open('data/ClubHeadData.json', 'r') as f:
    data = json.load(f)

swing_data = data['data']

print(f"Total samples: {len(swing_data)}")

# Find address (lowest speed in first 20%)
search_end = len(swing_data) // 5
speeds = []
for i in range(min(search_end, len(swing_data)-1)):
    if i == 0:
        speeds.append(0)
    else:
        q1 = [swing_data[i-1]['q0'], swing_data[i-1]['q1'], swing_data[i-1]['q2'], swing_data[i-1]['q3']]
        q2 = [swing_data[i]['q0'], swing_data[i]['q1'], swing_data[i]['q2'], swing_data[i]['q3']]
        angle_diff = quaternion_angle_difference(q1, q2)
        speeds.append(angle_diff)

address_idx = np.argmin(speeds)
address_quat = [swing_data[address_idx]['q0'], swing_data[address_idx]['q1'], 
                swing_data[address_idx]['q2'], swing_data[address_idx]['q3']]

print(f"Address at sample #{address_idx}")
print(f"Address quat: q0={address_quat[0]:.4f}, q1={address_quat[1]:.4f}, q2={address_quat[2]:.4f}, q3={address_quat[3]:.4f}")

# Calculate orientation difference from address for ALL samples
orientation_diffs = []
all_speeds = []

for i in range(len(swing_data)):
    quat = [swing_data[i]['q0'], swing_data[i]['q1'], swing_data[i]['q2'], swing_data[i]['q3']]
    diff = quaternion_angle_difference(address_quat, quat)
    orientation_diffs.append(diff)
    
    # Calculate speed
    if i == 0:
        all_speeds.append(0)
    else:
        prev_quat = [swing_data[i-1]['q0'], swing_data[i-1]['q1'], swing_data[i-1]['q2'], swing_data[i-1]['q3']]
        speed = quaternion_angle_difference(prev_quat, quat)
        all_speeds.append(speed)

# Find impact using both methods
speed_based_impact = np.argmax(all_speeds)
orientation_based_impact = np.argmin(orientation_diffs)

print(f"\n🚀 SPEED-based impact: sample #{speed_based_impact}")
print(f"   Speed: {all_speeds[speed_based_impact]:.2f}°/sample")
print(f"   Orientation diff from address: {orientation_diffs[speed_based_impact]:.2f}°")

print(f"\n🎯 ORIENTATION-based impact: sample #{orientation_based_impact}")
print(f"   Speed: {all_speeds[orientation_based_impact]:.2f}°/sample")
print(f"   Orientation diff from address: {orientation_diffs[orientation_based_impact]:.2f}°")

# Find the point with BOTH high speed AND close orientation
# Look for minimum orientation difference in the high-speed region
high_speed_threshold = np.max(all_speeds) * 0.7  # 70% of max speed
high_speed_indices = np.where(np.array(all_speeds) > high_speed_threshold)[0]

if len(high_speed_indices) > 0:
    # Among high-speed samples, find closest orientation to address
    high_speed_diffs = [orientation_diffs[i] for i in high_speed_indices]
    best_idx_in_region = np.argmin(high_speed_diffs)
    combined_impact = high_speed_indices[best_idx_in_region]
    
    print(f"\n⚡ COMBINED (high speed + close orientation): sample #{combined_impact}")
    print(f"   Speed: {all_speeds[combined_impact]:.2f}°/sample")
    print(f"   Orientation diff from address: {orientation_diffs[combined_impact]:.2f}°")
else:
    combined_impact = speed_based_impact

# Plot orientation difference and speed over time
plt.figure(figsize=(14, 8))

plt.subplot(2, 1, 1)
plt.plot(orientation_diffs, 'b-', label='Orientation difference from address')
plt.axhline(y=15, color='g', linestyle='--', alpha=0.5, label='Good threshold (15°)')
plt.axhline(y=30, color='orange', linestyle='--', alpha=0.5, label='Moderate threshold (30°)')
plt.axvline(x=address_idx, color='green', linestyle='-', linewidth=2, label=f'Address (#{address_idx})')
plt.axvline(x=speed_based_impact, color='red', linestyle='-', linewidth=2, label=f'Speed Impact (#{speed_based_impact})')
plt.axvline(x=orientation_based_impact, color='blue', linestyle='-', linewidth=2, label=f'Orient Impact (#{orientation_based_impact})')
if combined_impact != speed_based_impact:
    plt.axvline(x=combined_impact, color='purple', linestyle='-', linewidth=2, label=f'Combined (#{combined_impact})')
plt.xlabel('Sample Number')
plt.ylabel('Orientation Difference (degrees)')
plt.title('Club Orientation vs Address Position')
plt.legend()
plt.grid(True, alpha=0.3)

plt.subplot(2, 1, 2)
plt.plot(all_speeds, 'r-', label='Angular speed')
plt.axvline(x=address_idx, color='green', linestyle='-', linewidth=2, label=f'Address (#{address_idx})')
plt.axvline(x=speed_based_impact, color='red', linestyle='-', linewidth=2, label=f'Speed Impact (#{speed_based_impact})')
plt.axvline(x=orientation_based_impact, color='blue', linestyle='-', linewidth=2, label=f'Orient Impact (#{orientation_based_impact})')
if combined_impact != speed_based_impact:
    plt.axvline(x=combined_impact, color='purple', linestyle='-', linewidth=2, label=f'Combined (#{combined_impact})')
plt.xlabel('Sample Number')
plt.ylabel('Angular Speed (degrees/sample)')
plt.title('Club Head Angular Speed')
plt.legend()
plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('impact_detection_analysis.png', dpi=150)
print(f"\n📊 Graph saved to: impact_detection_analysis.png")
plt.show()

# Recommendation
print(f"\n💡 RECOMMENDATION:")
if orientation_diffs[speed_based_impact] > 30:
    print(f"   The speed-based impact (#{speed_based_impact}) has orientation {orientation_diffs[speed_based_impact]:.1f}° from address.")
    print(f"   This is too large for accurate contact. Consider:")
    print(f"   1. Re-calibrate the sensor (it may have shifted)")
    print(f"   2. Use orientation-based impact detection (sample #{orientation_based_impact})")
    print(f"   3. Check if sensor is securely mounted")
elif orientation_diffs[speed_based_impact] > 15:
    print(f"   Moderate orientation difference at impact ({orientation_diffs[speed_based_impact]:.1f}°)")
    print(f"   This suggests the club face was open/closed at impact.")
else:
    print(f"   Good orientation match at impact ({orientation_diffs[speed_based_impact]:.1f}°)")
    print(f"   The club returned close to address position.")
