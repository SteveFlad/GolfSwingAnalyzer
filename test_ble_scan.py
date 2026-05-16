"""
BLE Device Scanner - Diagnostic Tool
Continuously scans for BLE devices to help diagnose connection issues
"""

import time
from datetime import datetime

try:
    from ble_capture import scan_ble_devices_sync, BLEAK_AVAILABLE
except ImportError:
    print("Error: Could not import ble_capture module")
    exit(1)

def main():
    if not BLEAK_AVAILABLE:
        print("ERROR: bleak library not installed!")
        print("Install with: pip install bleak")
        return
    
    print("=" * 70)
    print("BLE DEVICE SCANNER - Press Ctrl+C to stop")
    print("=" * 70)
    print("\nThis tool will scan for BLE devices every 5 seconds.")
    print("Look for 'GolfSwingAnalyzer' or 'XIAO_ESP32S3' or similar names.\n")
    
    scan_count = 0
    devices_seen = {}  # Track all devices we've seen
    
    try:
        while True:
            scan_count += 1
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Scan #{scan_count} - Searching for devices...")
            
            devices = scan_ble_devices_sync(timeout=5.0)
            
            if not devices:
                print("  ❌ No devices found in this scan")
            else:
                print(f"  ✓ Found {len(devices)} device(s):")
                
                # Sort by RSSI (signal strength) - strongest first
                devices.sort(key=lambda d: d.rssi, reverse=True)
                
                for device in devices:
                    # Track when we last saw this device
                    devices_seen[device.address] = {
                        'name': device.name,
                        'rssi': device.rssi,
                        'last_seen': scan_count
                    }
                    
                    # Highlight potential ESP32/Golf Analyzer devices
                    name_upper = device.name.upper()
                    is_target = any(keyword in name_upper for keyword in 
                                  ['GOLF', 'SWING', 'ANALYZER', 'XIAO', 'ESP32'])
                    
                    marker = "🎯 **TARGET**" if is_target else ""
                    signal = "📶 Strong" if device.rssi > -60 else "📶 Weak" if device.rssi > -80 else "📶 Very Weak"
                    
                    print(f"    • {device.name}")
                    print(f"      Address: {device.address}")
                    print(f"      Signal: {device.rssi} dBm {signal} {marker}")
                    
            # Show summary of all devices we've seen
            if scan_count % 3 == 0 and devices_seen:  # Every 3 scans
                print(f"\n  📊 SUMMARY: Seen {len(devices_seen)} unique device(s) total:")
                for addr, info in devices_seen.items():
                    scans_ago = scan_count - info['last_seen']
                    status = "ACTIVE" if scans_ago == 0 else f"Last seen {scans_ago} scan(s) ago"
                    print(f"    - {info['name']} ({addr}): {status}")
            
            print("\n  ⏳ Waiting 5 seconds before next scan...")
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("SCAN STOPPED")
        print("=" * 70)
        
        if devices_seen:
            print(f"\n📋 FINAL REPORT - Detected {len(devices_seen)} unique device(s):")
            for addr, info in devices_seen.items():
                print(f"  • {info['name']}")
                print(f"    Address: {addr}")
                print(f"    Best RSSI: {info['rssi']} dBm")
                print()
        else:
            print("\n❌ No BLE devices were detected during the scan.")
            print("\nTROUBLESHOOTING:")
            print("  1. Make sure your ESP32 is powered on")
            print("  2. Check that Bluetooth is enabled on your computer")
            print("  3. Try resetting the ESP32 (unplug and replug)")
            print("  4. Ensure the firmware is flashed correctly")
            print("  5. Check ESP32 serial output: pio device monitor")

if __name__ == "__main__":
    main()
