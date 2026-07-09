"""
Comprehensive ESP32 Detection Script
Uses multiple methods to find connected ESP32 devices
"""
import serial.tools.list_ports
import subprocess
import sys

print("=" * 70)
print("ESP32 DETECTION - Multiple Methods")
print("=" * 70)

# Method 1: PySerial enumeration
print("\n[Method 1] PySerial Port Scan:")
print("-" * 70)
all_ports = serial.tools.list_ports.comports()
if not all_ports:
    print("  ❌ No COM ports found at all!")
else:
    for port in all_ports:
        print(f"\n  Port: {port.device}")
        print(f"    Description: {port.description}")
        print(f"    Hardware ID: {port.hwid}")
        print(f"    Manufacturer: {port.manufacturer}")
        print(f"    Product: {port.product}")
        print(f"    Serial Number: {port.serial_number}")
        
        # Check for known ESP32 identifiers
        is_esp32 = False
        reasons = []
        
        # VID/PID patterns
        if 'VID:PID=10C4:EA60' in port.hwid.upper():
            is_esp32 = True
            reasons.append("CP2102 USB-UART (common for ESP32)")
        if 'VID:PID=1A86:7523' in port.hwid.upper():
            is_esp32 = True
            reasons.append("CH340 USB-UART (common for ESP32)")
        if 'VID:PID=0403:6001' in port.hwid.upper():
            is_esp32 = True
            reasons.append("FTDI USB-UART")
        if 'VID:PID=303A' in port.hwid.upper():
            is_esp32 = True
            reasons.append("ESP32-S3 native USB")
        if 'VID:PID=2341' in port.hwid.upper():
            is_esp32 = True
            reasons.append("Arduino/Seeeduino device")
            
        # Description patterns
        if any(x in port.description.upper() for x in ['CP210', 'CH340', 'USB-SERIAL', 'USB SERIAL']):
            if 'BLUETOOTH' not in port.description.upper():
                is_esp32 = True
                reasons.append("USB-Serial adapter")
        
        if is_esp32:
            print(f"    🎯 LIKELY ESP32: {', '.join(reasons)}")
        elif 'BLUETOOTH' in port.description.upper():
            print(f"    ℹ️  Bluetooth port (not USB)")
        else:
            print(f"    ❓ Unknown device")

# Method 2: ESPTool auto-detection
print("\n\n[Method 2] ESPTool Auto-Detection:")
print("-" * 70)
try:
    # Run esptool with auto port detection
    result = subprocess.run(
        [sys.executable, '-m', 'esptool', 'chip_id'],
        capture_output=True,
        text=True,
        timeout=10
    )
    if 'Detecting chip type' in result.stdout or result.returncode == 0:
        print("  ✅ ESPTool found a device!")
        print(result.stdout)
    else:
        print("  ❌ ESPTool couldn't detect any ESP32")
        if result.stderr:
            print(f"  Error: {result.stderr}")
except subprocess.TimeoutExpired:
    print("  ⏱️  Timeout - no device responded")
except Exception as e:
    print(f"  ❌ Error running esptool: {e}")

# Method 3: Try connecting to each non-Bluetooth port
print("\n\n[Method 3] Direct Connection Test:")
print("-" * 70)
test_ports = [p for p in all_ports if 'BLUETOOTH' not in p.description.upper()]

if not test_ports:
    print("  ❌ No non-Bluetooth serial ports to test")
else:
    for port in test_ports:
        print(f"\n  Testing {port.device} ({port.description})...")
        try:
            ser = serial.Serial(port.device, 115200, timeout=1)
            print(f"    ✅ Opened successfully at 115200 baud")
            
            # Try to read data
            ser.reset_input_buffer()
            data = ser.read(100)
            if data:
                print(f"    📡 Receiving data ({len(data)} bytes):")
                try:
                    decoded = data.decode('utf-8', errors='ignore')
                    print(f"       {decoded[:100]}")
                except:
                    print(f"       {data[:50]}")
            else:
                print(f"    📭 No data (device may be idle)")
            
            ser.close()
        except serial.SerialException as e:
            print(f"    ❌ Cannot open: {e}")
        except Exception as e:
            print(f"    ❌ Error: {e}")

# Summary
print("\n" + "=" * 70)
print("SUMMARY:")
print("=" * 70)

usb_serial_ports = [p for p in all_ports if 'BLUETOOTH' not in p.description.upper()]
if not usb_serial_ports:
    print("❌ NO USB SERIAL DEVICES DETECTED")
    print("\nPossible reasons:")
    print("  1. ESP32 not connected via USB cable")
    print("  2. USB cable is charge-only (no data pins)")
    print("  3. Driver not installed")
    print("  4. Device in bootloader mode or not powered")
    print("  5. USB port or cable malfunction")
    print("\nTroubleshooting steps:")
    print("  1. Try a different USB cable")
    print("  2. Try a different USB port on your computer")
    print("  3. Press the RESET button on the ESP32")
    print("  4. Install CH340/CP2102 drivers if needed")
    print("  5. Check Device Manager for unknown devices")
else:
    print(f"✅ Found {len(usb_serial_ports)} USB serial device(s):")
    for p in usb_serial_ports:
        print(f"   - {p.device}: {p.description}")
