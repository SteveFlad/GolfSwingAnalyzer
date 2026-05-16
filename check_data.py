import json
import numpy as np

# Load data
with open('data/ClubHeadData.json', 'r') as f:
    data = json.load(f)

print(f"Total points: {len(data['data'])}")
print(f"\nFirst quaternion: q0={data['data'][0]['q0']:.4f}, q1={data['data'][0]['q1']:.4f}, q2={data['data'][0]['q2']:.4f}, q3={data['data'][0]['q3']:.4f}")
print(f"Middle quaternion: q0={data['data'][len(data['data'])//2]['q0']:.4f}, q1={data['data'][len(data['data'])//2]['q1']:.4f}, q2={data['data'][len(data['data'])//2]['q2']:.4f}, q3={data['data'][len(data['data'])//2]['q3']:.4f}")
print(f"Last quaternion: q0={data['data'][-1]['q0']:.4f}, q1={data['data'][-1]['q1']:.4f}, q2={data['data'][-1]['q2']:.4f}, q3={data['data'][-1]['q3']:.4f}")

# Extract all quaternions
quats = np.array([[d['q0'], d['q1'], d['q2'], d['q3']] for d in data['data']])

print(f"\nQuaternion ranges:")
print(f"  Q0: {quats[:,0].min():.4f} to {quats[:,0].max():.4f} (range: {quats[:,0].max() - quats[:,0].min():.4f})")
print(f"  Q1: {quats[:,1].min():.4f} to {quats[:,1].max():.4f} (range: {quats[:,1].max() - quats[:,1].min():.4f})")
print(f"  Q2: {quats[:,2].min():.4f} to {quats[:,2].max():.4f} (range: {quats[:,2].max() - quats[:,2].min():.4f})")
print(f"  Q3: {quats[:,3].min():.4f} to {quats[:,3].max():.4f} (range: {quats[:,3].max() - quats[:,3].min():.4f})")

# Calculate differences between consecutive quaternions
diffs = np.diff(quats, axis=0)
diff_magnitudes = np.linalg.norm(diffs, axis=1)
print(f"\nQuaternion differences:")
print(f"  Mean change: {diff_magnitudes.mean():.6f}")
print(f"  Max change: {diff_magnitudes.max():.6f}")
print(f"  Min change: {diff_magnitudes.min():.6f}")
print(f"  Number of zero changes: {np.sum(diff_magnitudes == 0)}")
print(f"  Number of tiny changes (<0.001): {np.sum(diff_magnitudes < 0.001)}")
print(f"  Number of significant changes (>0.01): {np.sum(diff_magnitudes > 0.01)}")

# Calculate angular changes
from scipy.spatial.transform import Rotation
rotations = Rotation.from_quat(quats[:, [1, 2, 3, 0]])  # scipy uses x,y,z,w format
angular_changes = []
for i in range(1, len(rotations)):
    rel_rot = rotations[i-1].inv() * rotations[i]
    angle = rel_rot.magnitude()  # radians
    angular_changes.append(angle)

angular_changes = np.array(angular_changes)
print(f"\nAngular changes (degrees):")
print(f"  Mean: {np.rad2deg(angular_changes.mean()):.3f}°")
print(f"  Max: {np.rad2deg(angular_changes.max()):.3f}°")
print(f"  Min: {np.rad2deg(angular_changes.min()):.3f}°")
print(f"  >1° changes: {np.sum(angular_changes > np.deg2rad(1))}")
print(f"  >5° changes: {np.sum(angular_changes > np.deg2rad(5))}")
print(f"  >10° changes: {np.sum(angular_changes > np.deg2rad(10))}")
