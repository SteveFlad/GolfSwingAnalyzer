"""
AB Shutter 6 - Direct BLE Connection (Bypasses Windows Driver)
This avoids the "Driver error" by connecting directly via BLE
"""

import asyncio
from bleak import BleakScanner, BleakClient
import time

DEVICE_NAME = "AB Shutter"

class ABShutterDirectBLE:
    """Direct BLE connection - no Windows driver needed"""
    
    def __init__(self, callback=None):
        self.callback = callback
        self.device = None
        self.client = None
        self.is_connected = False
        
    async def scan(self, timeout=10):
        """Find the AB Shutter device"""
        print(f"Scanning for {DEVICE_NAME}...")
        print("Make sure remote is ON and NOT paired with Windows\n")
        
        devices = await BleakScanner.discover(timeout=timeout)
        
        for device in devices:
            if device.name and DEVICE_NAME in device.name:
                self.device = device
                print(f"✓ Found: {device.name} ({device.address})")
                return True
        
        print(f"✗ '{DEVICE_NAME}' not found")
        print("\nTroubleshooting:")
        print("1. Remove device from Windows Bluetooth settings")
        print("2. Turn remote OFF then ON")
        print("3. Run this script again\n")
        return False
    
    def button_callback(self, sender, data):
        """Handle button press notifications"""
        print(f"\n🔘 Button Pressed!")
        print(f"   Data: {data.hex()}")
        
        if self.callback:
            self.callback(data)
    
    async def connect_and_listen(self):
        """Connect and listen for button presses"""
        if not self.device:
            print("Run scan() first!")
            return
        
        try:
            print(f"\nConnecting to {self.device.name}...")
            
            async with BleakClient(self.device.address, timeout=15.0) as client:
                self.client = client
                self.is_connected = True
                
                print(f"✓ Connected!")
                print(f"\nDiscovering services...")
                
                # Find all characteristics that support notifications
                for service in client.services:
                    for char in service.characteristics:
                        if "notify" in char.properties:
                            print(f"  Subscribing to: {char.uuid}")
                            try:
                                await client.start_notify(char.uuid, self.button_callback)
                            except Exception as e:
                                print(f"    Could not subscribe: {e}")
                
                print(f"\n✓ Ready! Press buttons on remote...")
                print("  (Press Ctrl+C to stop)\n")
                
                # Keep connection alive
                while True:
                    await asyncio.sleep(1)
                    
        except asyncio.TimeoutError:
            print("\n✗ Connection timeout - device might be too far or out of battery")
        except Exception as e:
            print(f"\n✗ Connection error: {e}")
            print("\nTry:")
            print("1. Remove device from Windows Bluetooth")
            print("2. Turn remote OFF for 5 seconds")
            print("3. Turn back ON and retry")
        finally:
            self.is_connected = False

async def main():
    """Test the AB Shutter via direct BLE"""
    print("="*60)
    print("AB Shutter 6 - Direct BLE Connection Test")
    print("="*60)
    print("\n⚠️  IMPORTANT: Device must NOT be paired with Windows!")
    print("   Go to: Settings → Bluetooth → Remove 'AB Shutter'\n")
    
    input("Press Enter when device is unpaired...")
    print()
    
    shutter = ABShutterDirectBLE()
    
    # Step 1: Scan
    if not await shutter.scan():
        return
    
    # Step 2: Connect and listen
    try:
        await shutter.connect_and_listen()
    except KeyboardInterrupt:
        print("\n\n✓ Stopped")

if __name__ == "__main__":
    asyncio.run(main())
