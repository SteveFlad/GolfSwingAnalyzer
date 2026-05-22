# PROPER CALIBRATION TECHNIQUE

## CRITICAL: Use USB Connection
Calibration REQUIRES USB cable connection (not Bluetooth).
Use the same USB cable you use to flash firmware.

---

## Position 1: ADDRESS
**Purpose:** Captures gravity direction when shaft is angled

**How to hold:**
- Club head ON THE GROUND (or hovering 1" above)
- Shaft at normal address angle (~60-70 degrees from ground)
- Face square to imaginary target
- Stand behind club as if you're about to hit a ball
- Hold STEADY for full 2-3 seconds during collection

**Common mistake:** Lifting club off ground - NO! Keep it down.

---

## Position 2: TOE UP  
**Purpose:** Identifies toe-heel axis

**How to hold:**
- LIFT club to waist height
- Hold HORIZONTALLY (parallel to ground)
- Rotate so TOE (top edge of club) points straight UP to sky
- Heel (bottom edge) points DOWN to ground  
- Face should be perpendicular to ground (pointing sideways)
- Hold STEADY for 2-3 seconds

**Common mistake:** Keeping club at address - NO! Lift to waist height.

---

## Position 3: TOE DOWN
**Purpose:** Confirms toe-heel direction

**How to hold:**
- Keep club at waist height
- Still HORIZONTAL
- Rotate OPPOSITE direction - TOE now points DOWN
- Heel points UP to sky
- Face perpendicular to ground
- Hold STEADY for 2-3 seconds

---

## Position 4: FACE UP
**Purpose:** Captures face normal direction

**How to hold:**
- Lay club flat on its BACK (like it's lying down to rest)
- Face pointing straight UP at ceiling
- Imagine the face is a mirror - you should see your reflection
- Shaft horizontal (can rest on table/bench at waist height)
- Hold STEADY for 2-3 seconds

**Common mistake:** Holding club vertically - NO! Lay it flat.

---

## After Sensor Calibration: Set Address Reference

After completing the 4 positions above, you'll set the ADDRESS REFERENCE:

**How to hold:**
- Place club at normal address position (where you'd actually hit ball)
- Club head behind imaginary ball
- Face square to target
- Normal address posture
- This position becomes your (0, 0, 0) reference point

All future swing measurements will be relative to this address position.

---

## Troubleshooting

**If calibration fails (NaN values):**
1. Check USB cable is plugged in firmly
2. ESP32 may not be sending data - try unplugging/replugging USB
3. Don't move during the 2-3 second collection period
4. Make sure you clicked "Collect Data" and waited for completion
5. Restart ESP32 and try again

**If positions seem wrong after calibration:**
- You may have mixed up toe-up and toe-down
- Or face-up wasn't truly horizontal
- Run calibration again, following positions exactly

---

## Quick Reference

1. ADDRESS: Head on ground, shaft angled
2. TOE UP: Waist height, horizontal, toe to sky
3. TOE DOWN: Waist height, horizontal, toe to ground  
4. FACE UP: Flat on back, face to ceiling
5. ADDRESS REFERENCE: Normal ball address position
