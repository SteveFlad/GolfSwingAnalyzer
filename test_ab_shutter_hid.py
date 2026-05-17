"""
Alternative test for AB Shutter 6 - tries HID polling approach
Some remotes don't send notifications but expose HID reports that can be polled
"""

import asyncio
from bleak import BleakScanner, BleakClient
import sys

# Standard HID service and characteristic UUIDs
HID_SERVICE = "00001812-0000-1000-8000-00805f9b34fb"
HID_REPORT = "00002a4d-0000-1000-8000-00805f9b34fb"
HID_REPORT_MAP = "00002a4b-0000-1000-8000-00805f9b34fb"

DEVICE_NAME = "AB Shutter"

async def test_hid_remote():
    """Test AB Shutter 6 with HID polling"""
    print("="*60)
    print("AB Shutter 6 HID Polling Test")
    print("="*60 + "\n")
    
    # Scan for device
    print(f"Scanning for '{DEVICE_NAME}' device...")
    devices = await BleakScanner.discover(timeout=10)
    
    device = None
    for d in devices:
        if d.name and DEVICE_NAME in d.name:
            device = d
            print(f"✓ Found: {d.name} ({d.address})\n")
            break
    
    if not device:
        print(f"✗ Device not found!")
        print("\nDiscovered devices:")
        for d in devices:
            print(f"  - {d.name or 'Unknown'} ({d.address})")
        return
    
    # Connect and test
    async with BleakClient(device.address) as client:
        print(f"✓ Connected\n")
        
        print("All services and characteristics:")
        print("-" * 60)
        
        hid_report_chars = []
        all_readable_chars = []
        
        for service in client.services:
            print(f"\n📦 Service: {service.uuid}")
            if service.description != "Unknown":
                print(f"   {service.description}")
            
            for char in service.characteristics:
                props = char.properties
                print(f"   └─ {char.uuid} [{', '.join(props)}]")
                
                # Collect HID report characteristics
                if char.uuid.lower() == HID_REPORT.lower():
                    hid_report_chars.append(char)
                    print(f"      🎯 HID Report Characteristic!")
                
                # Collect all readable characteristics
                if "read" in props:
                    all_readable_chars.append(char)
                
                # Try to read any readable characteristic
                if "read" in props:
                    try:
                        value = await client.read_gatt_char(char.uuid)
                        if len(value) > 0 and len(value) <= 20:
                            print(f"      Current value: {value.hex()} ({list(value)})")
                    except Exception as e:
                        print(f"      (read failed: {e})")
        
        print("\n" + "="*60)
        
        if hid_report_chars:
            print(f"Found {len(hid_report_chars)} HID Report characteristic(s)")
            print("\nPolling for button presses (press button on remote)...")
            print("Press Ctrl+C to stop\n")
            
            last_values = {}
            for char in hid_report_chars:
                try:
                    last_values[char.uuid] = await client.read_gatt_char(char.uuid)
                except:
                    last_values[char.uuid] = bytes()
            
            try:
                while True:
                    await asyncio.sleep(0.05)  # Poll 20 times per second
                    
                    for char in hid_report_chars:
                        try:
                            value = await client.read_gatt_char(char.uuid)
                            if value != last_values[char.uuid]:
                                print(f"🔘 BUTTON CHANGE DETECTED on {char.uuid}!")
                                print(f"   Old: {last_values[char.uuid].hex()}")
                                print(f"   New: {value.hex()}")
                                print(f"   Bytes: {list(value)}\n")
                                last_values[char.uuid] = value
                        except Exception as e:
                            pass
                            
            except KeyboardInterrupt:
                print("\n✓ Stopping...")
        else:
            print("No HID Report characteristics found.")
            print(f"\nTrying notification approach on ALL characteristics...")
            print("Press button on remote...\n")
            
            button_pressed = False
            
            def notification_handler(sender, data):
                nonlocal button_pressed
                print(f"🔘 NOTIFICATION from {sender}!")
                print(f"   Data: {data.hex()}")
                print(f"   Bytes: {list(data)}\n")
                button_pressed = True
            
            # Subscribe to everything that supports notify
            for service in client.services:
                for char in service.characteristics:
                    if "notify" in char.properties or "indicate" in char.properties:
                        try:
                            await client.start_notify(char.uuid, notification_handler)
                            print(f"  ✓ Monitoring {char.uuid}")
                        except:
                            pass
            
            print("\n✓ Listening... press button now")
            print("Press Ctrl+C to stop\n")
            
            try:
                while True:
                    await asyncio.sleep(0.1)
            except KeyboardInterrupt:
                print("\n✓ Stopping...")

if __name__ == "__main__":
    try:
        asyncio.run(test_hid_remote())
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)
