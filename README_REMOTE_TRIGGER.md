# AB Shutter 6 Remote Integration Guide

## Overview

Integration of ASHUTB AB Shutter 6 Bluetooth remote to trigger golf swing capture hands-free.

## Setup Options

### Option 1: Keyboard Input (Recommended - Simplest)

**Requirements:**
- AB Shutter 6 paired with Windows as a Bluetooth keyboard
- Python `keyboard` package (in requirements.txt)
- May require administrator privileges

**Advantages:**
- No BLE library needed
- Works like any keyboard
- Reliable connection
- No custom pairing code

**How it works:**
1. Pair AB Shutter with Windows (Settings → Bluetooth → Add device)
2. Remote sends keyboard commands (e.g., Volume Up, Enter)
3. Python `keyboard` library captures these events
4. Triggers `start_recording()` or `stop_recording()` in main.py

**Files:**
- `remote_trigger.py` - Main implementation
- `test_key_detective.py` - Discovers which keys the remote sends

### Option 2: Direct BLE Connection (Advanced)

**Requirements:**
- Device must be unpaired from Windows
- `bleak` BLE library
- Custom characteristic discovery

**Advantages:**
- Direct control
- Can read battery level
- No Windows driver issues

**Disadvantages:**
- More complex
- Connection can be unstable
- Device must stay unpaired from Windows

**Files:**
- `test_ab_shutter.py` - Notification-based detection
- `test_ab_shutter_hid.py` - HID polling detection

## Integration Steps (Keyboard Method)

### Step 1: Discover the Key Code

Run the detective script:
```powershell
python test_key_detective.py
```

Press the AB Shutter button and note the key name (e.g., "volume up", "enter", etc.)

### Step 2: Test the Remote Trigger

Edit `remote_trigger.py` if needed to match your key, then test:
```powershell
python remote_trigger.py
```

### Step 3: Integrate into main.py

Add to the top of `main.py`:
```python
try:
    from remote_trigger import RemoteTrigger
    REMOTE_AVAILABLE = True
except ImportError:
    REMOTE_AVAILABLE = False
```

In the `__init__` method, add:
```python
# Remote trigger setup
self.remote_trigger = None
if REMOTE_AVAILABLE:
    self.remote_trigger = RemoteTrigger(callback=self.on_remote_button)
```

Add the callback method:
```python
def on_remote_button(self, key_name):
    """Handle remote button press"""
    if not self.monitoring:
        # Start recording
        self.log_status(f"🔘 Remote trigger: Starting capture...")
        self.start_recording()
    else:
        # Stop recording
        self.log_status(f"🔘 Remote trigger: Stopping capture...")
        self.stop_recording()
```

In `start_recording()`, add:
```python
# Start remote trigger if available
if self.remote_trigger and not self.remote_trigger.is_listening:
    self.remote_trigger.start()
```

In `stop_recording()`, add:
```python
# Stop remote trigger
if self.remote_trigger and self.remote_trigger.is_listening:
    self.remote_trigger.stop()
```

Add checkbox to UI (in `create_widgets()`):
```python
# Remote trigger checkbox
if REMOTE_AVAILABLE:
    self.remote_enabled = tk.BooleanVar(value=True)
    remote_check = ttk.Checkbutton(
        control_frame,
        text="Enable Remote Trigger",
        variable=self.remote_enabled
    )
    remote_check.pack(side=tk.LEFT, padx=5)
```

### Step 4: Test the Integration

1. Pair AB Shutter with Windows
2. Run main.py (as administrator if needed)
3. Connect to your ESP32 sensor
4. Press remote button to start capture
5. Make a swing
6. Press remote button again to stop

## Troubleshooting

### No keys detected
- **Run as administrator**: keyboard library needs elevated privileges
- **Test in Notepad**: Press button - does it type anything?
- **Check pairing**: Is device connected in Windows Bluetooth settings?
- **Battery**: Is the remote battery good?

### Remote works in Notepad but not in script
- Run VS Code as administrator
- Check Windows security settings

### Connection drops
- Move closer to PC
- Replace remote battery
- Remove and re-pair device

### Driver error in Windows
- Device Manager → Bluetooth → Find AB Shutter
- Right-click → Update driver → "Bluetooth HID Device"
- Or uninstall device, restart, re-pair

## Alternative: Media Key Detection

If the remote sends media keys (common), you might need to listen for these instead:
```python
TRIGGER_KEYS = ['volume up', 'volume down', 'play/pause', 'next track', 'previous track']
```

Some remotes have multiple buttons - you can map them differently:
- Android button (📷): Start capture
- iOS button (🍎): Stop capture

## Testing Without Remote

You can test the integration using regular keyboard keys:
1. Temporarily set `TRIGGER_KEYS = ['f9']`
2. Press F9 key instead of remote
3. Once verified, change back to actual remote keys

## Battery Monitoring (BLE Method Only)

If using the BLE connection approach, you can read battery level:
```python
# In test_ab_shutter_hid.py, add:
battery_char = "00002a19-0000-1000-8000-00805f9b34fb"
battery_level = await client.read_gatt_char(battery_char)
print(f"Battery: {battery_level[0]}%")
```

## Future Enhancements

- Voice feedback: "Recording started", "Recording stopped"
- LED indicator when capturing
- Multi-button mapping (start, stop, visualize, calibrate)
- Auto-reconnect if connection drops
- Battery level display in GUI
- Vibration feedback (if remote supports it)

## Resources

- Python keyboard library: https://github.com/boppreh/keyboard
- Bleak BLE library: https://github.com/hbldh/bleak
- Windows HID documentation: https://learn.microsoft.com/en-us/windows-hardware/drivers/hid/
