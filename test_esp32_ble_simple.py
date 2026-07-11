"""
Simple BLE connection test - just attempts connection without data transfer
"""
import asyncio
from bleak import BleakClient, BleakScanner

DEVICE_ADDRESS = "B8:F8:62:FC:53:D5"

async def test_connection():
    print("=" * 60)
    print("ESP32 BLE Hardware Test")
    print("=" * 60)
    
    print("\n1. Scanning for device...")
    devices = await BleakScanner.discover(timeout=5.0)
    found = False
    for d in devices:
        if d.address == DEVICE_ADDRESS:
            rssi = getattr(d, 'rssi', 'N/A')
            print(f"✓ Found: {d.name or 'Unknown'} ({d.address}) RSSI: {rssi}")
            found = True
            break
    
    if not found:
        print("✗ Device not found in scan - ESP32 may not be advertising")
        return False
    
    print("\n2. Attempting connection...")
    try:
        async with BleakClient(DEVICE_ADDRESS, timeout=10.0) as client:
            print(f"✓ Connected: {client.is_connected}")
            
            print("\n3. Reading GATT services...")
            services = client.services
            print(f"✓ Found {len(services)} services")
            
            for service in services:
                print(f"  Service: {service.uuid}")
                for char in service.characteristics:
                    print(f"    - Characteristic: {char.uuid} (Properties: {char.properties})")
            
            print("\n✓ BLE hardware appears to be working!")
            return True
            
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        print("\nThis suggests a hardware or pairing issue.")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_connection())
    print("\n" + "=" * 60)
    if result:
        print("VERDICT: BLE hardware is functional")
        print("Issue may be software/configuration related")
    else:
        print("VERDICT: BLE hardware may be defective")
        print("Consider replacement or check pairing/power settings")
    print("=" * 60)
