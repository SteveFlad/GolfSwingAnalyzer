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
print(f"Total samples: {len(data)}\n")

# Club length (46" driver)
club_length_m = 1.168

# Calculate positions for first, middle, and last samples
positions = []
for i in [0, len(data)//4, len(data)//2, 3*len(data)//4, len(data)-1]:
    q = data[i]
    quat_xyzw = [q['q1'], q['q2'], q['q3'], q['q0']]  # Convert to scipy format
    
    # Club head position = rotation applied to [0, 0, club_length]
    club_head = rotate_vector_by_quaternion(quat_xyzw, [0, 0, club_length_m])
    positions.append(club_head)
    
    print(f"Sample {i:3d}: X={club_head[0]:6.3f}m, Y={club_head[1]:6.3f}m, Z={club_head[2]:6.3f}m")

print("\n=== Movement Analysis ===")
start_pos = np.array(positions[0])
end_pos = np.array(positions[-1])

movement = end_pos - start_pos
print(f"Total movement from start to end:")
print(f"  ΔX (Target Line): {movement[0]:6.3f}m ({movement[0]*3.28:.2f}ft)")
print(f"  ΔY (Height):      {movement[1]:6.3f}m ({movement[1]*3.28:.2f}ft)")
print(f"  ΔZ (In/Out):      {movement[2]:6.3f}m ({movement[2]*3.28:.2f}ft)")

# Calculate ranges
all_positions = []
for d in data:
    quat_xyzw = [d['q1'], d['q2'], d['q3'], d['q0']]
    pos = rotate_vector_by_quaternion(quat_xyzw, [0, 0, club_length_m])
    all_positions.append(pos)

all_positions = np.array(all_positions)
print(f"\n=== Full Swing Ranges ===")
print(f"X range (Target Line): {all_positions[:,0].min():.3f} to {all_positions[:,0].max():.3f} m (range: {np.ptp(all_positions[:,0])*3.28:.2f} ft)")
print(f"Y range (Height):      {all_positions[:,1].min():.3f} to {all_positions[:,1].max():.3f} m (range: {np.ptp(all_positions[:,1])*3.28:.2f} ft)")
print(f"Z range (In/Out):      {all_positions[:,2].min():.3f} to {all_positions[:,2].max():.3f} m (range: {np.ptp(all_positions[:,2])*3.28:.2f} ft)")

print("\n=== Interpretation ===")
ranges = [np.ptp(all_positions[:,0]), np.ptp(all_positions[:,1]), np.ptp(all_positions[:,2])]
axis_names = ['X (Target Line)', 'Y (Height)', 'Z (In/Out)']

max_movement_idx = np.argmax(ranges)
print(f"Primary swing movement is in: {axis_names[max_movement_idx]}")
print(f"  This is the axis with the most range: {ranges[max_movement_idx]*3.28:.2f} ft")

print("\nGolf swing expectations:")
print("  - Target Line (X): Small movement (club stays near ball)")
print("  - Height (Y): Moderate movement (club goes up in backswing)")
print("  - In/Out (Z): Large movement (club goes back, then through)")
