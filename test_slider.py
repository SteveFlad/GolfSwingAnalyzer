"""
Test slider functionality with filtered data range
"""

import json
import numpy as np
from visualizer import SwingVisualizer
from sensor_calibration import SensorCalibration

# Load calibration if available
calibration = SensorCalibration('calibration_data.json')

# Load data
with open('data/ClubHeadData.json', 'r') as f:
    data = json.load(f)

print(f"Loaded {len(data['data'])} samples")

# Create visualizer with calibration
viz = SwingVisualizer(data['data'], calibration=calibration)

print("\nProcessing data...")
# Data is already processed in __init__

print(f"Impact detected at sample #{viz.impact_idx}")
print(f"Impact speed: {viz.velocities[viz.impact_idx] * viz.rad_to_mph:.1f} mph")

# Show visualization with slider controls
print("\nShowing visualization with slider controls...")
print("Use sliders to filter the visible data range")
print("- Start Sample: Controls the beginning of the visible range")
print("- End Sample: Controls the end of the visible range")
print("- Reset button: Returns to full swing view")
print("- Impact button: Focuses on ±50 samples around impact")

viz.show()
