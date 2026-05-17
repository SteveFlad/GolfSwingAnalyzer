# AB Shutter 6 - Windows HID Driver Fix Guide

## The Problem
AB Shutter 6 uses Bluetooth HID (keyboard) protocol, but Windows doesn't have the right driver.
This causes "Driver error" and immediate disconnection.

## Solution: Force Generic HID Driver

### Step 1: Open Device Manager as Administrator
```powershell
Start-Process devmgmt.msc -Verb RunAs
```

### Step 2: Show Hidden Devices
1. In Device Manager, click **View** menu
2. Check **"Show hidden devices"**

### Step 3: Find the AB Shutter
1. Expand **"Bluetooth"** section
2. Look for "AB Shutter" or "Unknown Bluetooth Device"
3. If you see a yellow warning triangle, that's it!

### Step 4: Update Driver Manually
1. Right-click the device → **Update driver**
2. Choose **"Browse my computer for drivers"**
3. Choose **"Let me pick from a list of available drivers"**
4. Look for **"Generic Bluetooth Radio"** or **"HID-compliant device"**
5. Select it and click **Next**

### Step 5: Re-pair Device
1. Remove device from Bluetooth settings
2. Turn remote OFF and back ON
3. Pair again

## If That Doesn't Work...

### Alternative 1: Use Different Pairing Mode
Some AB Shutters have multiple modes (iOS/Android):
- Hold BOTH buttons for 5-10 seconds
- LED will blink differently = mode changed
- Try pairing in each mode

### Alternative 2: Different Trigger Methods

#### A) Foot Pedal (USB)
- Search: "USB foot pedal keyboard"
- Acts as Enter/Space key
- Reliable, no Bluetooth issues
- $15-30 on Amazon

#### B) Wireless Keyboard (Logitech/Microsoft)
- Any reliable Bluetooth keyboard
- Use specific key as trigger
- Already has Windows drivers

#### C) Smartphone App
- Create simple app that sends HTTP request
- ESP32 can host web server
- Trigger via phone button

#### D) Physical Button on Glove
- Small tactile button on golf glove
- Wire to ESP32 GPIO pin
- Most reliable option

## Recommended: Physical GPIO Button

Since you already have ESP32, add a button:

```cpp
// In main.cpp
const int TRIGGER_PIN = 9;  // GPIO pin

void setup() {
    pinMode(TRIGGER_PIN, INPUT_PULLUP);
}

void loop() {
    if (digitalRead(TRIGGER_PIN) == LOW) {
        // Button pressed - start capture
        Serial.println("TRIGGER:START");
        delay(300);  // Debounce
    }
}
```

Python side:
```python
if "TRIGGER:START" in line:
    self.start_recording()
```

**Advantages:**
- No Bluetooth complexity
- 100% reliable
- Instant response
- No batteries needed
- Simple wiring
