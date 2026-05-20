# Quick Reference: Reading Your Golf Swing Graphs

## Graph Overview

Your swing analysis displays 5 graphs showing different aspects of club head movement:

### 1. 3D Trajectory (Large Left Panel)
**What it shows**: Complete club head path through 3D space

**How to read it**:
- **Green dot** = Start of swing (address position)
- **Red X** = End of swing
- **Gold star** = Impact with ball
- **Color gradient** = Speed (green=slow, yellow=medium, red=fast)
- **Blue line** = Club head path
- **Red arrows** = Direction of movement

**Coordinates displayed**:
- **X (left/right)**: Target Line position
  - Negative = left of target
  - Positive = right of target
  - Zero = on target line
  
- **Y (forward/back)**: In/Out position
  - Near zero = at ball
  - Positive = away from ball (backswing)
  
- **Z (up/down)**: Height from ground
  - Zero = ground level
  - Higher values = club raised

**Impact Data Box Shows**:
```
IMPACT
Position:
  Target Line (X): ±X.XX ft (left/right of target)
  In/Out (Y): Y.YY ft (near/away from ball)
  Height (Z): Z.ZZ ft (above ground)
Speed: XXX.X mph
Face Angle: ±X.X° (open/closed)
```

---

### 2. Club Head Speed (Top Right)
**What it shows**: How fast the club head is moving throughout the swing

**How to read it**:
- **X-axis**: Sample number (time progression)
- **Y-axis**: Speed in miles per hour (mph)
- **Blue line**: Speed over time
- **Red/Green dot**: Impact point or maximum speed
- **Orange dashed line**: Impact timing

**Typical patterns**:
- Starts near zero (address)
- Increases during backswing
- Peaks at or near impact
- Decreases after contact

**What to look for**:
- Maximum speed should occur at or just before impact
- Smooth acceleration curve
- Speed at impact (shown at marker)

---

### 3. Club Face Angle (Second Right)
**What it shows**: Club face orientation relative to target line throughout swing

**How to read it**:
- **X-axis**: Sample number (time progression)
- **Y-axis**: Angle in degrees
- **Green line**: Face angle over time
- **Black dashed line**: Square to target (0°)
- **Blue shading**: Closed face region
- **Red shading**: Open face region

**Angle Convention**:
- **0°** = Face square to target line
- **Positive (+)** = Face closed (pointing left of target for right-handed golfer)
- **Negative (-)** = Face open (pointing right of target for right-handed golfer)

**Key Markers**:
- **Blue dot**: Setup face angle (address position)
- **Red dot**: Face angle at impact

**What to look for**:
- Face angle at impact (most important!)
- How much face rotates during swing
- Face position at address vs impact

**Example Interpretations**:
- `Impact: +3.5°` = Face closed 3.5° (ball likely goes left)
- `Impact: -2.0°` = Face open 2° (ball likely goes right)
- `Impact: 0.5°` = Nearly square (ball should go straight)

---

### 4. Top View (Third Right)
**What it shows**: Bird's eye view of swing path (looking down from above)

**How to read it**:
- **X-axis**: Target Line (left/right)
- **Y-axis**: In/Out (toward/away from ball)
- **Colored dots**: Club head positions (colored by speed)
- **Red arrows**: Face direction at key points
- **Green dot**: Start position
- **Red X**: End position
- **Gold star**: Impact position
- **White circle**: Ball position

**What to look for**:
- Swing path shape (in-to-out, out-to-in, or straight)
- Club head position at impact relative to ball
- How far back club goes (backswing length)

---

### 5. Side View (Bottom Right)
**What it shows**: Swing path from target line perspective (as if standing on target line looking at golfer)

**How to read it**:
- **X-axis**: In/Out (toward/away from ball)
- **Y-axis**: Height from ground
- **Blue dashed line**: Ground level
- **Colored dots**: Club head positions (colored by speed)

**What to look for**:
- Height of backswing
- Lowest point of swing
- Height at impact (should be near ground for driver)
- Angle of attack (upward or downward at impact)

---

## Coordinate System Quick Reference

Always displayed above the sliders:
```
Golf Coordinates: 
  X = Target Line (±left/right) 
  Y = In/Out (ball/away) 
  Z = Height (ground/up)
```

**Remember**:
- All position values are in **feet**
- All speed values are in **miles per hour (mph)**
- All angles are in **degrees (°)**

---

## Interactive Controls

**Sample Range Sliders** (bottom):
- **Start Sample**: Move right to skip beginning of swing
- **End Sample**: Move left to skip end of swing
- Use to focus on specific portions (e.g., just downswing)

**Buttons**:
- **Reset**: Return to viewing full swing
- **Impact**: Auto-focus on ±50 samples around ball contact
- **3D View Buttons**: Change 3D perspective
  - Side View: Behind golfer
  - Down-Line: Opposite view
  - Top-Down: From above
  - Normal Stance: From the side

---

## Common Questions

**Q: What's a good club head speed?**
- Amateur average: 80-100 mph
- Good amateur: 100-110 mph
- Pro average: 110-120 mph
- Long drive: 130+ mph

**Q: What face angle should I aim for?**
- For straight shots: -1° to +1° (square)
- For draws: +2° to +4° (slightly closed)
- For fades: -2° to -4° (slightly open)

**Q: Why does the path look different from what I feel?**
- The graphs show actual 3D motion
- Our perception during swing can be different
- Trust the data over feel for analysis

**Q: What does "Max jump" mean in diagnostics?**
- Largest distance between consecutive samples
- Should be small for smooth swing
- Large values indicate erratic motion or sensor issues

---

## Tips for Analysis

1. **Start with 3D view**: Get overall sense of swing path
2. **Check speed graph**: Verify impact timing and maximum speed
3. **Examine face angle**: Most critical for ball flight direction
4. **Use top view**: Analyze swing path (inside-out vs outside-in)
5. **Check side view**: Verify height and angle of attack
6. **Use sliders**: Focus on backswing, transition, or downswing separately

---

## Exporting Data

Position data is saved in: `data/ClubHeadData.json`

Each point contains:
- Quaternion orientation (q0, q1, q2, q3)
- Timestamp (if available)

The visualizer calculates from this:
- Position (X, Y, Z)
- Speed
- Face angle

---

## Troubleshooting

**Graph looks jumpy or noisy?**
- Adjust filter settings in main application
- Try increasing smoothing window
- Check sensor connection quality

**Impact not detected?**
- Verify swing speed is reasonable (>30 mph)
- Check that full swing was captured
- Impact detection requires speed drop after peak

**Face angle seems wrong?**
- Verify sensor calibration (run calibration wizard)
- Check sensor mounting orientation
- Ensure sensor is securely attached to club
