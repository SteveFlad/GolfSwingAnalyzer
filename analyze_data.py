import json
import numpy as np

# Load the data
with open('data/ClubHeadData.json', 'r') as f:
    data = json.load(f)

print(f"Total data points: {len(data['data'])}")
print(f"\nFile timestamp: {data['timestamp']}")

# Extract quaternion components
q0_values = [d['q0'] for d in data['data']]
q1_values = [d['q1'] for d in data['data']]
q2_values = [d['q2'] for d in data['data']]
q3_values = [d['q3'] for d in data['data']]

print("\n=== Quaternion Value Ranges ===")
print(f"q0 (w): min={min(q0_values):.4f}, max={max(q0_values):.4f}, range={max(q0_values)-min(q0_values):.4f}")
print(f"q1 (x): min={min(q1_values):.4f}, max={max(q1_values):.4f}, range={max(q1_values)-min(q1_values):.4f}")
print(f"q2 (y): min={min(q2_values):.4f}, max={max(q2_values):.4f}, range={max(q2_values)-min(q2_values):.4f}")
print(f"q3 (z): min={min(q3_values):.4f}, max={max(q3_values):.4f}, range={max(q3_values)-min(q3_values):.4f}")

print("\n=== Sample Data ===")
print("First sample:", data['data'][0])
print("Middle sample:", data['data'][len(data['data'])//2])
print("Last sample:", data['data'][-1])

# Calculate angular changes between consecutive samples
angles = []
for i in range(1, len(data['data'])):
    q_prev = np.array([data['data'][i-1]['q0'], data['data'][i-1]['q1'], 
                       data['data'][i-1]['q2'], data['data'][i-1]['q3']])
    q_curr = np.array([data['data'][i]['q0'], data['data'][i]['q1'], 
                       data['data'][i]['q2'], data['data'][i]['q3']])
    
    # Calculate angle between quaternions
    dot_product = np.dot(q_prev, q_curr)
    angle = 2 * np.arccos(min(abs(dot_product), 1.0))
    angles.append(np.degrees(angle))

print(f"\n=== Angular Changes ===")
print(f"Mean angular change: {np.mean(angles):.4f} degrees")
print(f"Max angular change: {np.max(angles):.4f} degrees")
print(f"Total angular movement: {np.sum(angles):.2f} degrees")
print(f"Samples with >1 degree change: {sum(1 for a in angles if a > 1.0)}")
print(f"Samples with >5 degree change: {sum(1 for a in angles if a > 5.0)}")

if np.max(angles) < 5.0:
    print("\n⚠️ WARNING: Very small movement detected!")
    print("This looks like the sensor was stationary or barely moving.")
    print("For a golf swing, expect 100-300+ degrees of total rotation.")
