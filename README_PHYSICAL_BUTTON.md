# Physical Button Trigger - Quick Setup Guide

## Why Use a Physical Button Instead of AB Shutter?
- ✅ **100% Reliable** - No Bluetooth driver issues
- ✅ **Instant Response** - No wireless lag
- ✅ **Simple** - Just 2 wires
- ✅ **No Batteries** - Uses ESP32's internal pull-up resistor

## Hardware Requirements
- **1x Momentary push button** (normally open)
  - Any tactile button, arcade button, or footswitch
  - Example: $1-5 on Amazon/AliExpress
- **2x Jumper wires** (or solder directly)

## Wiring Diagram

```
XIAO ESP32S3        Button
┌─────────┐         ┌───┐
│         │         │   │
│    GPIO9├─────────┤ 1 │  (Signal)
│         │         │   │
│     GND ├─────────┤ 2 │  (Ground)
│         │         └───┘
└─────────┘
```

### Pin Connections
- **Button Pin 1** → **GPIO9** (D8 on XIAO)
- **Button Pin 2** → **GND** (any ground pin)

### Notes
- ✅ Internal pull-up enabled - no external resistor needed
- ✅ Button press = GPIO9 → GND (LOW)
- ✅ Button release = GPIO9 → 3.3V (HIGH via pull-up)

## Mounting Options

### Option 1: Glove-Mounted Button
- Small tactile button sewn/glued to golf glove
- Press with thumb to start capture
- Thin wires run down arm to ESP32

### Option 2: Foot Pedal
- Larger button/footswitch on ground
- Step to trigger
- ESP32 in pocket or clip

### Option 3: Handle-Mounted
- Button on club grip or near hands
- Easy access during setup swing

## Firmware Changes
The firmware has been updated with:
- GPIO9 configured as input with pull-up
- Debounced button detection (300ms)
- Sends `TRIGGER:PRESSED` via Serial and BLE
- Visual feedback (LED blink) on press

## Python Integration

### Option A: Using button_trigger.py
```python
from button_trigger import ButtonTrigger

# In main.py __init__:
self.button_trigger = ButtonTrigger(callback=self.on_button_press)

# In serial monitor loop:
if "TRIGGER:" in line:
    if self.button_trigger.check_serial_data(line):
        if not self.monitoring:
            self.start_recording()
```

### Option B: Direct Integration
```python
# In your serial monitoring code:
if "TRIGGER:PRESSED" in line:
    if not self.monitoring:
        self.start_recording()
    else:
        self.stop_recording()
```

## Upload Firmware

```powershell
# Build and upload updated firmware
pio run -e seeed_xiao_esp32s3 -t upload

# Verify it works
pio device monitor
```

When you press the button, you should see:
```
TRIGGER:PRESSED
```

## Testing

1. **Wire the button** (GPIO9 to GND)
2. **Upload firmware** (command above)
3. **Open serial monitor**
4. **Press button** - should see "TRIGGER:PRESSED"
5. **LED blinks** briefly as visual confirmation

## Troubleshooting

**Button doesn't trigger:**
- Check wiring: GPIO9 and GND
- Verify button is normally-open type
- Test continuity with multimeter when pressed

**Multiple triggers from one press:**
- Normal - debounce catches most
- Increase `BUTTON_DEBOUNCE_MS` in main.cpp if needed

**Want different pin:**
- Change `#define TRIGGER_BUTTON_PIN 9` to desired GPIO
- Avoid: 5, 6 (I2C), 21 (LED), boot pins

## Cost Comparison

| Method | Cost | Reliability | Setup Time |
|--------|------|-------------|------------|
| **Physical Button** | **$1-5** | **99.9%** | **5 min** |
| AB Shutter 6 | $15-20 | ~60% (driver issues) | 30+ min troubleshooting |
| Foot Pedal (USB) | $20-30 | 95% | 10 min |
| Different BT Remote | $10-25 | Unknown (same driver risk) | Variable |

**Recommendation: Physical button is the best solution for this project.**
