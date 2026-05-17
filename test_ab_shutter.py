"""
Test script for AB Shutter 6 Bluetooth Remote
Detects button presses and prints the data received.
This will help us understand the protocol for integration into main.py
"""

import asyncio
from bleak import BleakScanner, BleakClient
import sys

# Common HID service UUID
HID_SERVICE_UUID = "00001812-0000-1000-8000-00805f9b34fb"
HID_REPORT_CHARACTERISTIC = "00002a4d-0000-1000-8000-00805f9b34fb"

# Device name to look for
DEVICE_NAME = "AB Shutter"  # Partial match for "AB Shutter 6"

class ABShutterTester:
    def __init__(self):
        self.device = None
        self.client = None
        self.button_pressed = False
        
    async def scan_for_device(self, timeout=10):
        """Scan for AB Shutter device"""
        print(f"Scanning for '{DEVICE_NAME}' device...")
        print("Make sure the device is in pairing mode (usually blinking LED)")
        print(f"Scanning for {timeout} seconds...\n")
        
        devices = await BleakScanner.discover(timeout=timeout)
        
        print(f"Found {len(devices)} Bluetooth devices:")
        for i, device in enumerate(devices):
            print(f"  {i+1}. {device.name or 'Unknown'} - {device.address}")
            if device.name and DEVICE_NAME in device.name:
                self.device = device
                print(f"\n✓ Found target device: {device.name} ({device.address})")
                
        if not self.device:
            print(f"\n✗ Could not find device matching '{DEVICE_NAME}'")
            print("Available devices listed above - check if it's visible")
            return False
            
        return True
    
    def notification_handler(self, sender, data):
        """Handle notifications from the device (button presses)"""
        print(f"\n🔘 BUTTON EVENT DETECTED!")
        print(f"   Sender: {sender}")
        print(f"   Data (hex): {data.hex()}")
        print(f"   Data (bytes): {list(data)}")
        print(f"   Length: {len(data)} bytes")
        
        # Decode common HID keyboard codes
        if len(data) >= 2:
            modifier = data[0]
            key_code = data[1] if len(data) > 1 else 0
            
            key_names = {
                0x00: "No key",
                0x28: "Enter",
                0x29: "Escape",
                0x2A: "Backspace",
                0x50: "Left Arrow",
                0x4F: "Right Arrow",
                0x52: "Up Arrow",
                0x51: "Down Arrow",
                0x42: "Volume Up",
                0x43: "Volume Down",
            }
            
            print(f"   Modifier: 0x{modifier:02x}")
            print(f"   Key Code: 0x{key_code:02x} ({key_names.get(key_code, 'Unknown')})")
        
        self.button_pressed = True
        
    async def connect_and_listen(self):
        """Connect to device and listen for button presses"""
        if not self.device:
            print("No device to connect to!")
            return
            
        print(f"\nConnecting to {self.device.name}...")
        
        try:
            async with BleakClient(self.device.address) as client:
                self.client = client
                print(f"✓ Connected: {client.is_connected}")
                
                # Discover all services and characteristics
                print("\nDiscovering services and characteristics...")
                notify_chars = []
                
                for service in client.services:
                    print(f"\n[Service] {service.uuid}")
                    print(f"  Description: {service.description}")
                    for char in service.characteristics:
                        properties = ", ".join(char.properties)
                        print(f"  └─ [Char] {char.uuid}")
                        print(f"     Properties: {properties}")
                        
                        # If characteristic supports notifications or indications, subscribe to it
                        if "notify" in char.properties or "indicate" in char.properties:
                            print(f"     → Will subscribe to notifications...")
                            notify_chars.append(char)
                
                # Subscribe to all notify-capable characteristics
                print(f"\n Subscribing to {len(notify_chars)} notification characteristics...")
                for char in notify_chars:
                    try:
                        await client.start_notify(char.uuid, self.notification_handler)
                        print(f"  ✓ Subscribed to {char.uuid}")
                    except Exception as e:
                        print(f"  ✗ Failed to subscribe to {char.uuid}: {e}")
                
                print("\n" + "="*60)
                print("✓ Listening for button presses...")
                print("  Press the button(s) on your AB Shutter 6 remote")
                print("  Press Ctrl+C to stop")
                print("="*60 + "\n")
                
                # Keep listening until interrupted
                try:
                    while True:
                        await asyncio.sleep(0.1)
                        if self.button_pressed:
                            # Reset flag for next press
                            self.button_pressed = False
                            
                except KeyboardInterrupt:
                    print("\n\nStopping...")
                    
        except Exception as e:
            print(f"\n✗ Error: {e}")
            print(f"   Type: {type(e).__name__}")
            import traceback
            traceback.print_exc()

async def main():
    """Main test function"""
    print("="*60)
    print("AB Shutter 6 Button Press Detector")
    print("="*60 + "\n")
    
    tester = ABShutterTester()
    
    # Scan for device
    found = await tester.scan_for_device(timeout=10)
    
    if not found:
        print("\nTroubleshooting:")
        print("1. Make sure device is powered on and in pairing mode")
        print("2. Remove it from Windows Bluetooth settings first")
        print("3. Some remotes need button press to wake up during scan")
        print("4. Try running this script again")
        return
    
    # Connect and listen
    await tester.connect_and_listen()
    
    print("\n✓ Test complete!")
    print("\nNext steps:")
    print("1. Review the data format printed above")
    print("2. We'll integrate this into main.py to trigger swing capture")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)
