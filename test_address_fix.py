"""
Test Address Normalization Fix
Loads your latest swing and checks if address is at (0, 0, 0)
"""

import json
import sys
sys.path.insert(0, '.')

from visualizer import SwingVisualizer
from sensor_calibration import SensorCalibration

print("=" * 70)
print("TESTING ADDRESS NORMALIZATION")
print("=" * 70)

# Load swing data
with open('data/ClubHeadData.json', 'r') as f:
    swing_data = json.load(f)

print(f"\n✓ Loaded swing with {len(swing_data['data'])} samples")
print(f"  Timestamp: {swing_data['timestamp']}")

# Load calibration
calibration = SensorCalibration()
print(f"\n✓ Loaded calibration")
print(f"  Has address reference: {calibration.has_address_reference}")
if calibration.has_address_reference:
    print(f"  Stored address face angle: {calibration.address_face_angle:.2f}°")

# Create visualizer (this processes the data)
print("\n" + "=" * 70)
print("PROCESSING SWING DATA")
print("=" * 70)

viz = SwingVisualizer(
    data=swing_data['data'],
    coordinate_system='ground',
    calibration=calibration,
    filename='Test Swing'
)

print("\n" + "=" * 70)
print("VERIFICATION")
print("=" * 70)

# Check address position
if hasattr(viz, 'address_idx'):
    address_pos = viz.positions[viz.address_idx]
    print(f"\n✓ Address detected at sample #{viz.address_idx}")
    print(f"  Position: X={address_pos[0]:.3f} m ({address_pos[0]*3.28084:.2f} ft)")
    print(f"            Y={address_pos[1]:.3f} m ({address_pos[1]*3.28084:.2f} ft)")
    print(f"            Z={address_pos[2]:.3f} m ({address_pos[2]*3.28084:.2f} ft)")
    
    address_face = viz.face_angles[viz.address_idx]
    print(f"  Face angle: {address_face:.2f}°")
    
    # Check if normalized
    pos_magnitude = (address_pos[0]**2 + address_pos[1]**2 + address_pos[2]**2)**0.5
    
    print("\n" + "=" * 70)
    if pos_magnitude < 0.01 and abs(address_face) < 1.0:
        print("✓ SUCCESS: Address is normalized to (0, 0, 0) with 0° face!")
        print("\nYour visualization should now show:")
        print("  Address: X=0.00 ft, Y=0.00 ft, Z=0.00 ft, Face=0.0°")
    else:
        print("❌ PROBLEM: Address is NOT at origin")
        print(f"  Distance from origin: {pos_magnitude:.3f} m ({pos_magnitude*3.28084:.2f} ft)")
        print(f"  Face angle offset: {address_face:.2f}°")
        print("\nThe fix may not be working correctly.")
else:
    print("\n❌ ERROR: No address index found")

print("=" * 70)
