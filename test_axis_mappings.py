import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
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

# Calculate all positions
all_positions = []
for d in data:
    quat_xyzw = [d['q1'], d['q2'], d['q3'], d['q0']]
    pos = rotate_vector_by_quaternion(quat_xyzw, [0, 0, club_length_m])
    all_positions.append(pos)

all_positions = np.array(all_positions) * m_to_ft  # Convert to feet

# Define all possible axis mappings
# Format: (indices, labels)
mappings = [
    ([0, 1, 2], "Original: X=Target, Y=Height, Z=In/Out"),
    ([0, 2, 1], "Swap Y↔Z: X=Target, Y=In/Out, Z=Height"),
    ([1, 0, 2], "Swap X↔Y: X=Height, Y=Target, Z=In/Out"),
    ([1, 2, 0], "Rotate: X=In/Out, Y=Height, Z=Target"),
    ([2, 0, 1], "Rotate: X=Height, Y=In/Out, Z=Target"),
    ([2, 1, 0], "Swap X↔Z: X=In/Out, Y=Height, Z=Target"),
]

# Create figure with 2x3 grid
fig = plt.figure(figsize=(18, 12))
gs = GridSpec(2, 3, figure=fig, hspace=0.3, wspace=0.3)

for idx, (mapping, label) in enumerate(mappings):
    ax = fig.add_subplot(gs[idx // 3, idx % 3], projection='3d')
    
    # Apply axis mapping
    mapped_pos = all_positions[:, mapping]
    
    # Calculate ranges for this mapping
    x_range = np.ptp(mapped_pos[:, 0])
    y_range = np.ptp(mapped_pos[:, 1])
    z_range = np.ptp(mapped_pos[:, 2])
    
    # Plot trajectory
    ax.plot(mapped_pos[:, 0], mapped_pos[:, 1], mapped_pos[:, 2], 
            'b-', linewidth=2, alpha=0.7)
    
    # Mark start and end
    ax.scatter(*mapped_pos[0], color='green', s=100, marker='o', label='Start', zorder=10)
    ax.scatter(*mapped_pos[-1], color='red', s=100, marker='X', label='End', zorder=10)
    
    # Mark impact (sample 225 from find_impact.py)
    impact_idx = 225
    if impact_idx < len(mapped_pos):
        ax.scatter(*mapped_pos[impact_idx], color='gold', s=300, marker='*', 
                  edgecolors='orange', linewidths=2, label='Impact', zorder=15)
    
    # Labels
    ax.set_xlabel('X - Target Line (ft)')
    ax.set_ylabel('Y - Height (ft)')
    ax.set_zlabel('Z - In/Out (ft)')
    ax.set_title(f'{label}\nRanges: X={x_range:.2f}ft, Y={y_range:.2f}ft, Z={z_range:.2f}ft',
                fontsize=10, pad=10)
    ax.legend(loc='upper left', fontsize=8)
    
    # Add text annotation with ideal ranges
    ideal_text = "IDEAL:\nX≈1-2ft\nY≈4-6ft\nZ≈6-8ft"
    ax.text2D(0.02, 0.98, ideal_text, transform=ax.transAxes,
             fontsize=8, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # Color code based on how well it matches ideal
    # Ideal: X small (1-2), Y moderate (4-6), Z large (6-8)
    x_score = abs(x_range - 1.5)  # Want ~1.5ft
    y_score = abs(y_range - 5.0)  # Want ~5ft
    z_score = abs(z_range - 7.0)  # Want ~7ft
    total_score = x_score + y_score + z_score
    
    # Add score as background color
    if total_score < 3:  # Good match
        ax.set_facecolor((0.9, 1.0, 0.9))  # Light green
    elif total_score < 6:  # Okay match
        ax.set_facecolor((1.0, 1.0, 0.9))  # Light yellow
    else:  # Poor match
        ax.set_facecolor((1.0, 0.95, 0.95))  # Light red

fig.suptitle('Axis Mapping Comparison - Find the Best Golf Swing Orientation', 
            fontsize=14, fontweight='bold')

# Add explanation text at bottom
fig.text(0.5, 0.02, 
        'Look for: Small X movement (club near ball), Moderate Y (backswing height), Large Z (swing arc back→through)',
        ha='center', fontsize=11, style='italic',
        bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))

plt.savefig('axis_mapping_comparison.png', dpi=150, bbox_inches='tight')
print("\n" + "="*70)
print("AXIS MAPPING COMPARISON COMPLETE")
print("="*70)
print("\nAnalyzing all 6 possible axis orientations...\n")

for idx, (mapping, label) in enumerate(mappings):
    mapped_pos = all_positions[:, mapping]
    x_range = np.ptp(mapped_pos[:, 0])
    y_range = np.ptp(mapped_pos[:, 1])
    z_range = np.ptp(mapped_pos[:, 2])
    
    # Calculate score
    x_score = abs(x_range - 1.5)
    y_score = abs(y_range - 5.0)
    z_score = abs(z_range - 7.0)
    total_score = x_score + y_score + z_score
    
    status = "✓✓✓ BEST" if total_score < 3 else "✓✓ GOOD" if total_score < 6 else "✗ POOR"
    
    print(f"[{idx+1}] {label}")
    print(f"    X={x_range:.2f}ft (want 1-2)  Y={y_range:.2f}ft (want 4-6)  Z={z_range:.2f}ft (want 6-8)")
    print(f"    Score: {total_score:.2f}  {status}")
    print()

print("="*70)
print("Chart saved to: axis_mapping_comparison.png")
print("="*70)
print("\nLook at the chart - the best mapping will have:")
print("  • Light GREEN background (good match to ideal)")
print("  • Swing arc goes mostly BACK and THROUGH (Z axis)")
print("  • Moderate height change (Y axis)")
print("  • Stays close to ball laterally (X axis)")

plt.show()
