"""
AB Shutter 6 - Complete Service Scanner
This discovers ALL characteristics and shows which one sends button data
"""

import asyncio
from bleak import BleakScanner, BleakClient
import time

DEVICE_NAME = "AB Shutter"

class ABShutterScanner:
    """Comprehensive BLE scanner for AB Shutter"""
    
    def __init__(self):
        self.device = None
        self.client = None
        
    async def scan(self, timeout=10):
        """Find the AB Shutter device"""
        print(f"Scanning for {DEVICE_NAME}...")
        
        devices = await BleakScanner.discover(timeout=timeout)
        
        for device in devices:
            if device.name and DEVICE_NAME in device.name:
                self.device = device
                print(f"✓ Found: {device.name} ({device.address})\n")
                return True
        
        print(f"✗ '{DEVICE_NAME}' not found")
        return False
    
    def on_notification(self, sender, data):
        """Handle ANY notification from ANY characteristic"""
        print(f"\n{'='*60}")
        print(f"📡 NOTIFICATION RECEIVED!")
        print(f"{'='*60}")
        print(f"Characteristic UUID: {sender}")
        print(f"Data (hex):  {data.hex()}")
        print(f"Data (int):  {list(data)}")
        print(f"Data (len):  {len(data)} bytes")
        
        # Try to decode as text
        try:
            text = data.decode('utf-8')
            print(f"Data (text): '{text}'")
        except:
            pass
        
        print(f"{'='*60}\n")
    
    async def connect_and_monitor(self):
        """Connect and subscribe to ALL notification-capable characteristics"""
        if not self.device:
            print("Run scan() first!")
            return
        
        try:
            print(f"Connecting to {self.device.name}...")
            
            async with BleakClient(self.device.address, timeout=15.0) as client:
                self.client = client
                print(f"✓ Connected!\n")
                
                print("="*60)
                print("SCANNING ALL SERVICES AND CHARACTERISTICS")
                print("="*60)
                
                notify_count = 0
                
                for service in client.services:
                    print(f"\n📦 Service: {service.uuid}")
                    print(f"   Description: {service.description}")
                    
                    for char in service.characteristics:
                        props = ", ".join(char.properties)
                        print(f"\n   📌 Characteristic: {char.uuid}")
                        print(f"      Properties: {props}")
                        
                        # Subscribe to anything that can notify
                        if "notify" in char.properties or "indicate" in char.properties:
                            try:
                                await client.start_notify(char.uuid, self.on_notification)
                                print(f"      ✓ SUBSCRIBED to notifications")
                                notify_count += 1
                            except Exception as e:
                                print(f"      ✗ Could not subscribe: {e}")
                
                print(f"\n{'='*60}")
                print(f"✓ Subscribed to {notify_count} characteristics")
                print(f"{'='*60}")
                print(f"\n🔘 NOW PRESS BUTTONS ON THE REMOTE!")
                print(f"   Any data received will be shown above")
                print(f"   Press Ctrl+C to stop\n")
                
                # Keep connection alive and monitor
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    print("\n\n✓ Stopping...")
                    
        except asyncio.TimeoutError:
            print("\n✗ Connection timeout")
        except Exception as e:
            print(f"\n✗ Error: {e}")

async def main():
    """Main test function"""
    print("="*60)
    print("AB Shutter 6 - Complete Characteristic Scanner")
    print("="*60)
    print("\n⚠️  Device must be UNPAIRED from Windows!\n")
    
    scanner = ABShutterScanner()
    
    # Step 1: Find device
    if not await scanner.scan():
        return
    
    # Step 2: Connect and monitor everything
    await scanner.connect_and_monitor()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✓ Stopped")
