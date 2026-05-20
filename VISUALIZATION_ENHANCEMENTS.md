# Golf Swing Visualizer Enhancements

## Summary of Changes

The visualizer has been enhanced to provide comprehensive club head tracking data with improved labeling and a new club face angle graph.

## New Features

### 1. **Enhanced 3D Trajectory Display**
- **Clear Axis Labeling**: All axes now clearly labeled as:
  - **X-axis (Target Line)**: Left/Right position relative to target
  - **Y-axis (In/Out)**: Distance toward/away from ball
  - **Z-axis (Height)**: Vertical position from ground
  
- **Position Annotations**: 
  - Start position shows X, Y, Z coordinates in feet
  - End position shows X, Y, Z coordinates in feet
  - Impact position shows comprehensive data:
    - Position: Target Line (X), In/Out (Y), Height (Z) in feet
    - Speed in mph
    - Club face angle in degrees

- **Improved Diagnostic Info**:
  - Trajectory ranges displayed for all three axes
  - Total path length
  - Maximum jump between samples

### 2. **New Club Face Angle Graph**
- **Real-time tracking** of club face orientation relative to target line
- **Color-coded regions**:
  - Blue shading = Closed face (pointing left of target)
  - Red shading = Open face (pointing right of target)
  - Black dashed line = Square to target (0°)
  
- **Key Markers**:
  - Setup angle (first sample) marked with blue dot
  - Impact angle (if detected) marked with red dot
  - Continuous line showing face angle throughout swing

- **Convention**:
  - Positive angle = Closed face (left of target for right-handed)
  - Negative angle = Open face (right of target for right-handed)
  - 0° = Square to target line

### 3. **Enhanced Graph Layout**
The visualization now displays 5 graphs:

1. **3D Trajectory** (large, left side):
   - Full club head path in 3D space
   - Color-coded by speed
   - Velocity direction arrows
   - Impact marker with comprehensive data
   
2. **Club Head Speed** (top right):
   - Speed in mph over time
   - Impact point highlighted
   
3. **Club Face Angle** (second right):
   - Face orientation relative to target line
   - Setup and impact angles marked
   
4. **Top View** (third right):
   - Target Line vs In/Out (bird's eye view)
   - Face direction arrows at key points
   
5. **Side View** (bottom right):
   - In/Out vs Height (view from target line)
   - Ground reference line

### 4. **Coordinate System Legend**
A comprehensive coordinate system reference is now displayed above the sliders:
- **X = Target Line** (±left/right)
- **Y = In/Out** (ball/away)
- **Z = Height** (ground/up)

### 5. **Improved Axis Labels**
All graphs now have descriptive axis labels that clearly indicate:
- Which axis represents which measurement
- Direction convention (arrows showing positive/negative direction)
- Units (feet for position, mph for speed, degrees for angle)

## Data Display at Each Point

The enhanced visualizer tracks and displays the following at each captured point:

1. **Position (X, Y, Z)**:
   - X: Target Line position in feet
   - Y: In/Out position in feet
   - Z: Height from ground in feet

2. **Speed**:
   - Angular velocity converted to linear speed in mph
   - Based on club length (default 46" driver = 1.168m)

3. **Club Face Angle**:
   - Orientation relative to target line setup
   - Calculated from quaternion orientation data
   - Displayed in degrees (positive = closed, negative = open)

## Using the Enhanced Visualization

### Interactive Controls
- **Start/End Sample Sliders**: Filter the visible data range
- **Reset Button**: Return to full swing view
- **Impact Button**: Focus on ±50 samples around impact
- **3D View Buttons**: 
  - Side View: Behind golfer looking toward ball
  - Down-Line: Opposite side view
  - Top-Down: Bird's eye view
  - Normal Stance: Face-on view from side

### Reading the Data

**At Address (Start)**:
- Position annotation shows setup coordinates
- Face angle graph shows initial club face orientation

**During Swing**:
- 3D trajectory shows club head path
- Speed graph shows acceleration/deceleration
- Face angle graph shows how face opens/closes through swing

**At Impact**:
- Gold star marker on 3D plot
- Detailed annotation with:
  - Exact position (X, Y, Z)
  - Club head speed
  - Face angle at contact
- Highlighted on all graphs

## Technical Details

### Face Angle Calculation
The club face angle is calculated by:
1. Extracting face normal vector from quaternion orientation
2. Projecting onto horizontal plane (X-Y plane)
3. Computing angle relative to target line (X-axis)
4. Converting to golf convention (0° = square, +/- = closed/open)

### Coordinate Transformation
Sensor coordinates are mapped to golf coordinates:
- Sensor X → Golf -Z (height, inverted)
- Sensor Y → Golf X (target line)
- Sensor Z → Golf Y (in/out)

## Known Issues

- Minor `tight_layout` warning when rendering - does not affect functionality
- Very minor layout adjustment needed for optimal button placement with 4 graphs

## Future Enhancements

Potential additions:
- Club path plane visualization
- Attack angle calculation
- Dynamic loft at impact
- Swing plane analysis
- Comparison overlay for multiple swings
