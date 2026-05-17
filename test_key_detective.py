"""
Debug script to see what key the AB Shutter 6 actually sends
Captures ALL keyboard input
"""

import keyboard
import time

print("="*60)
print("AB Shutter Key Detective")
print("="*60)
print("\n1. Make sure AB Shutter 6 is paired with Windows")
print("2. Press SPACE BAR on your keyboard - you should see it detected")
print("3. Press buttons on AB Shutter - see what keys it sends")
print("4. Press Ctrl+C to stop\n")
print("Listening to ALL keyboard events...\n")

last_time = 0
debounce = 0.2  # seconds

def on_any_key(event):
    """Capture any key press"""
    global last_time
    current_time = time.time()
    
    # Debounce to avoid spam
    if current_time - last_time < debounce:
        return
    last_time = current_time
    
    print(f"KEY DETECTED:")
    print(f"  Name: '{event.name}'")
    print(f"  Scan code: {event.scan_code}")
    print(f"  Event type: {event.event_type}")
    print(f"  Is keypad: {event.is_keypad}")
    print()

# Hook all key events
keyboard.on_press(on_any_key)

try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\n\nStopping...")
    keyboard.unhook_all()
