"""
AB Shutter 6 Remote Trigger for Golf Swing Analyzer
Uses keyboard input detection - works when remote is paired with Windows
No BLE library needed!

The AB Shutter sends keyboard commands (usually Volume Up/Down)
This module detects those keys and triggers swing capture.
"""

import keyboard
import threading
import time

class RemoteTrigger:
    """Detects AB Shutter button presses via keyboard input"""
    
    # Common keys sent by AB Shutter remotes
    TRIGGER_KEYS = ['volume up', 'volume down', 'enter', 'space']
    
    def __init__(self, callback=None):
        """
        Args:
            callback: Function to call when button pressed. Signature: callback(key_name)
        """
        self.callback = callback
        self.is_listening = False
        self.listener_thread = None
        self.last_press_time = 0
        self.debounce_ms = 300  # Ignore repeated presses within 300ms
        
    def on_key_press(self, event):
        """Handle key press events"""
        key_name = event.name.lower()
        
        # Check if it's one of our trigger keys
        if key_name in [k.replace(' ', '') for k in self.TRIGGER_KEYS]:
            # Debounce - ignore if pressed too recently
            current_time = time.time() * 1000
            if current_time - self.last_press_time < self.debounce_ms:
                return
            
            self.last_press_time = current_time
            
            print(f"🔘 Remote button pressed: {key_name}")
            
            if self.callback:
                try:
                    self.callback(key_name)
                except Exception as e:
                    print(f"Error in callback: {e}")
    
    def start(self):
        """Start listening for button presses"""
        if self.is_listening:
            print("Already listening")
            return
        
        self.is_listening = True
        
        # Hook all trigger keys
        for key in self.TRIGGER_KEYS:
            try:
                keyboard.on_press_key(key, self.on_key_press)
            except:
                pass  # Some key names might not be valid
        
        print(f"✓ Remote trigger active - listening for: {', '.join(self.TRIGGER_KEYS)}")
        print("  Make sure AB Shutter 6 is paired with Windows")
        
    def stop(self):
        """Stop listening"""
        if not self.is_listening:
            return
        
        keyboard.unhook_all()
        self.is_listening = False
        print("✓ Remote trigger stopped")

def test_remote():
    """Test the remote trigger"""
    print("="*60)
    print("AB Shutter 6 Remote Trigger Test")
    print("="*60)
    print("\n1. Make sure AB Shutter 6 is PAIRED with Windows Bluetooth")
    print("2. Press any button on the remote")
    print("3. You should see a message below when pressed")
    print("4. Press Ctrl+C to stop\n")
    
    def on_button_press(key_name):
        print(f"  → Would trigger swing capture here!")
        print(f"  → Key detected: {key_name}\n")
    
    trigger = RemoteTrigger(callback=on_button_press)
    trigger.start()
    
    try:
        print("Waiting for button presses...\n")
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\nStopping...")
        trigger.stop()

if __name__ == "__main__":
    test_remote()
