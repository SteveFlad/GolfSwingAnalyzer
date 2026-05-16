"""Quick analysis of captured swing data to verify full swing motion"""
import json
import numpy as np
from scipy.spatial.transform import Rotation

# Load data
with open('data/ClubHeadData.json', 'r') as f:
    swing_data = json.load(f)

data = swing_data['data']
print(f"Analyzing swing captured at: {swing_data['timestamp']}")
print(f"Total samples: {swing_data['data_points']}")
print(f"Duration: {swing_data['data_points'] / 100:.2f} seconds (at 100 Hz)\n")

# Convert to quaternions (scipy format: x,y,z,w)
quats = np.array([[d['q1'], d['q2'], d['q3'], d['q0']] for d in data])

# Calculate angular velocities between samples
angular_changes = []
for i in range(1, len(quats)):
    r1 = Rotation.from_quat(quats[i-1])
    r2 = Rotation.from_quat(quats[i])
    
    # Rotation difference
    r_diff = r2 * r1.inv()
    angle_rad = r_diff.magnitude()
    angular_changes.append(np.degrees(angle_rad))

angular_changes = np.array(angular_changes)

# Calculate cumulative rotation
total_rotation = np.sum(angular_changes)

# Find peak velocity period (likely downswing)
window = 10  # 0.1 second window at 100Hz
peak_windows = []
for i in range(len(angular_changes) - window):
    window_sum = np.sum(angular_changes[i:i+window])
    peak_windows.append(window_sum)

peak_idx = np.argmax(peak_windows)
peak_velocity = peak_windows[peak_idx] * 10  # deg/s

print("=== ROTATION ANALYSIS ===")
print(f"Max angular change (single sample): {np.max(angular_changes):.2f}°")
print(f"Mean angular change: {np.mean(angular_changes):.3f}°")
print(f"Std dev: {np.std(angular_changes):.3f}°")
print(f"Total rotation: {total_rotation:.1f}°")
print(f"Peak velocity (0.1s window): {peak_velocity:.1f}°/s")
print(f"Peak occurs at sample: {peak_idx} ({peak_idx/100:.2f}s into swing)")

# Analyze pattern
print("\n=== SWING PATTERN ===")
# Divide into thirds to see if there's backswing/downswing pattern
third = len(angular_changes) // 3
first_third_avg = np.mean(angular_changes[:third])
second_third_avg = np.mean(angular_changes[third:2*third])
last_third_avg = np.mean(angular_changes[2*third:])

print(f"First third avg motion: {first_third_avg:.3f}°/sample")
print(f"Middle third avg motion: {second_third_avg:.3f}°/sample")
print(f"Last third avg motion: {last_third_avg:.3f}°/sample")

# Count significant movements
sig_movements = np.sum(angular_changes > 1.0)  # Changes > 1 degree
print(f"\nSignificant movements (>1°): {sig_movements}/{len(angular_changes)} ({sig_movements/len(angular_changes)*100:.1f}%)")

# Show first 10 and last 10 changes
print("\n=== FIRST 10 SAMPLES ===")
for i in range(min(10, len(angular_changes))):
    print(f"Sample {i}: {angular_changes[i]:.3f}°")

print("\n=== LAST 10 SAMPLES ===")
for i in range(max(0, len(angular_changes)-10), len(angular_changes)):
    print(f"Sample {i}: {angular_changes[i]:.3f}°")

# Show around peak velocity
print(f"\n=== AROUND PEAK VELOCITY (sample {peak_idx}) ===")
start = max(0, peak_idx - 5)
end = min(len(angular_changes), peak_idx + 15)
for i in range(start, end):
    marker = " <<<< PEAK" if i == peak_idx else ""
    print(f"Sample {i}: {angular_changes[i]:.3f}°{marker}")

print("\n=== VERDICT ===")
if total_rotation > 500 and peak_velocity > 500:
    print("✓ YES - This looks like a FULL SWING!")
    print(f"  Total rotation {total_rotation:.0f}° and peak {peak_velocity:.0f}°/s are consistent with driver swing")
elif total_rotation > 200 and peak_velocity > 200:
    print("⚠ PARTIAL - This looks like a partial swing or practice motion")
    print(f"  Total rotation {total_rotation:.0f}° and peak {peak_velocity:.0f}°/s are below full swing values")
else:
    print("✗ NO - This looks like minimal movement (hand/wrist motion only)")
    print(f"  Total rotation {total_rotation:.0f}° and peak {peak_velocity:.0f}°/s suggest sitting at desk")

print("\n=== REFERENCE VALUES ===")
print("Full driver swing: 800-1500° total rotation, 1500-3000°/s peak velocity")
print("Partial swing: 300-800° total rotation, 500-1500°/s peak velocity")
print("Hand motion: <200° total rotation, <500°/s peak velocity")
