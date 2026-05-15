import json
import numpy as np
import matplotlib.pyplot as plt

# Load the data
with open('data/ClubHeadData.json', 'r') as f:
    data = json.load(f)

print(f"Analyzing {len(data['data'])} samples for ball impact...\n")

# Calculate angular velocities between samples
angular_velocities = []
timestamps = []

for i in range(1, len(data['data'])):
    q_prev = np.array([data['data'][i-1]['q0'], data['data'][i-1]['q1'], 
                       data['data'][i-1]['q2'], data['data'][i-1]['q3']])
    q_curr = np.array([data['data'][i]['q0'], data['data'][i]['q1'], 
                       data['data'][i]['q2'], data['data'][i]['q3']])
    
    # Calculate angle between quaternions (in radians)
    dot_product = np.dot(q_prev, q_curr)
    angle = 2 * np.arccos(min(abs(dot_product), 1.0))
    
    # Assume 100Hz sampling (0.01 seconds per sample)
    dt = 0.01
    angular_velocity = angle / dt  # rad/s
    
    angular_velocities.append(angular_velocity)
    timestamps.append(i * dt)

angular_velocities = np.array(angular_velocities)

# Convert to linear club head speed (assume 46" driver = 1.168m)
club_length = 1.168  # meters
linear_speeds_ms = angular_velocities * club_length  # m/s
linear_speeds_mph = linear_speeds_ms * 2.23694  # mph

# Find maximum speed (likely impact point)
max_speed_idx = np.argmax(linear_speeds_mph)
max_speed = linear_speeds_mph[max_speed_idx]
max_speed_time = timestamps[max_speed_idx]
max_speed_sample = max_speed_idx + 1

print("=" * 70)
print("IMPACT DETECTION ANALYSIS")
print("=" * 70)
print(f"\nMaximum club head speed: {max_speed:.1f} mph")
print(f"Occurred at: Sample #{max_speed_sample} ({max_speed_time:.2f} seconds)")

# Look for deceleration after peak (characteristic of ball contact)
if max_speed_idx < len(linear_speeds_mph) - 10:
    # Check speeds in 0.1 second window after peak
    post_impact_speeds = linear_speeds_mph[max_speed_idx:max_speed_idx+10]
    speed_drop = max_speed - np.min(post_impact_speeds)
    
    print(f"\nSpeed drop in next 0.1 sec: {speed_drop:.1f} mph")
    if speed_drop > 10:
        print("✓ Significant deceleration detected - likely ball contact!")
    else:
        print("⚠ Minimal deceleration - may be practice swing or miss")

# Find backswing start (first significant movement)
movement_threshold = 5.0  # mph
backswing_start = 0
for i, speed in enumerate(linear_speeds_mph):
    if speed > movement_threshold:
        backswing_start = i
        break

# Find top of backswing (minimum speed between start and impact)
top_of_backswing_idx = np.argmin(linear_speeds_mph[backswing_start:max_speed_idx]) + backswing_start
top_of_backswing_time = timestamps[top_of_backswing_idx]

print(f"\n" + "=" * 70)
print("SWING PHASES")
print("=" * 70)
print(f"Backswing start:   Sample #{backswing_start+1} ({timestamps[backswing_start]:.2f}s)")
print(f"Top of backswing:  Sample #{top_of_backswing_idx+1} ({top_of_backswing_time:.2f}s)")
print(f"Impact:            Sample #{max_speed_sample} ({max_speed_time:.2f}s)")
print(f"\nBackswing duration: {top_of_backswing_time - timestamps[backswing_start]:.2f} seconds")
print(f"Downswing duration: {max_speed_time - top_of_backswing_time:.2f} seconds")

# Show speeds around impact
print(f"\n" + "=" * 70)
print("SPEEDS AROUND IMPACT")
print("=" * 70)
print("Sample  | Time (s) | Speed (mph)")
print("-" * 40)
start_idx = max(0, max_speed_idx - 5)
end_idx = min(len(linear_speeds_mph), max_speed_idx + 6)
for i in range(start_idx, end_idx):
    marker = " <-- IMPACT" if i == max_speed_idx else ""
    print(f"{i+1:6d}  | {timestamps[i]:8.3f} | {linear_speeds_mph[i]:8.1f}{marker}")

# Create visualization
plt.figure(figsize=(14, 8))

# Plot 1: Full swing speed profile
plt.subplot(2, 1, 1)
plt.plot(timestamps, linear_speeds_mph, 'b-', linewidth=2, label='Club Head Speed')
plt.axvline(max_speed_time, color='r', linestyle='--', linewidth=2, label=f'Impact ({max_speed:.1f} mph)')
plt.axvline(top_of_backswing_time, color='g', linestyle='--', linewidth=1, label='Top of Backswing')
plt.xlabel('Time (seconds)')
plt.ylabel('Club Head Speed (mph)')
plt.title('Golf Swing Analysis - Club Head Speed Profile')
plt.grid(True, alpha=0.3)
plt.legend()

# Plot 2: Zoomed view around impact
plt.subplot(2, 1, 2)
impact_window = 0.2  # seconds
start_time = max(0, max_speed_time - impact_window)
end_time = min(timestamps[-1], max_speed_time + impact_window)
mask = (np.array(timestamps) >= start_time) & (np.array(timestamps) <= end_time)
plt.plot(np.array(timestamps)[mask], linear_speeds_mph[mask], 'b-', linewidth=3)
plt.axvline(max_speed_time, color='r', linestyle='--', linewidth=2, label=f'Impact at {max_speed_time:.3f}s')
plt.scatter([max_speed_time], [max_speed], color='r', s=200, zorder=5, marker='*')
plt.xlabel('Time (seconds)')
plt.ylabel('Club Head Speed (mph)')
plt.title('Impact Zone Detail (±0.2 seconds)')
plt.grid(True, alpha=0.3)
plt.legend()

plt.tight_layout()
plt.savefig('swing_impact_analysis.png', dpi=150)
print(f"\n✓ Visualization saved to: swing_impact_analysis.png")
plt.show()
