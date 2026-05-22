"""
Test Calibration Data Collection
Verifies that sensor sends valid RAW accelerometer data in calibration mode
"""

import time
import serial
import serial.tools.list_ports

# Find the COM port
ports = list(serial.tools.list_ports.comports())
esp_port = None

# First, try to find USB serial port (preferred)
for port in ports:
    desc_upper = port.description.upper()
    if any(keyword in desc_upper for keyword in ["CH340", "USB-SERIAL", "UART", "CP210", "FTDI"]):
        esp_port = port.device
        print(f"Found USB serial port: {port.device} ({port.description})")
        break

# If no USB found, ask user to specify
if not esp_port:
    print("No USB serial port auto-detected.")
    print("\nAvailable ports:")
    for port in ports:
        print(f"  {port.device}: {port.description}")
    
    print("\nNote: Bluetooth COM ports cannot be used for firmware calibration mode.")
    print("      Please connect ESP32 via USB cable.")
    
    user_port = input("\nEnter COM port (or press Enter to exit): ").strip()
    if user_port:
        esp_port = user_port.upper()
        if not esp_port.startswith("COM"):
            esp_port = "COM" + esp_port
    else:
        exit(1)

print(f"✓ Found ESP32 on port: {esp_port}")
print("\nConnecting...")

# Connect
try:
    ser = serial.Serial(esp_port, 115200, timeout=1)
    time.sleep(2)  # Wait for connection
    print("✓ Connected")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    exit(1)

# Flush any old data
ser.reset_input_buffer()
print("\nClearing buffer...")
time.sleep(0.5)

# Enable calibration mode
print("\n" + "=" * 70)
print("ENABLING CALIBRATION MODE")
print("=" * 70)
ser.write(b"CAL_START\n")
time.sleep(0.5)  # Wait for mode switch

# Read lines
print("\nReading data for 3 seconds...")
print("Expected format: RAW AX:# AY:# AZ:# GX:# GY:# GZ:#\n")

start_time = time.time()
raw_count = 0
quat_count = 0
error_count = 0

while time.time() - start_time < 3.0:
    if ser.in_waiting > 0:
        try:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                if line.startswith("RAW"):
                    raw_count += 1
                    if raw_count <= 10:  # Print first 10
                        print(f"✓ RAW #{raw_count}: {line}")
                elif line.startswith("Q0:"):
                    quat_count += 1
                    if quat_count == 1:
                        print(f"⚠ QUATERNION (should be RAW): {line}")
                elif line.startswith("[CAL]"):
                    print(f"✓ {line}")
                elif line.startswith("ERROR") or line.startswith("WARNING"):
                    error_count += 1
                    print(f"❌ {line}")
        except Exception as e:
            print(f"Parse error: {e}")
    time.sleep(0.01)

# Disable calibration mode
print("\n" + "=" * 70)
print("DISABLING CALIBRATION MODE")
print("=" * 70)
ser.write(b"CAL_STOP\n")
time.sleep(0.5)

# Read a few more lines to see mode switch
print("\nReading quaternion mode (should switch back to Q0:...)...\n")
end_time = time.time() + 2.0
final_quat_count = 0
while time.time() < end_time:
    if ser.in_waiting > 0:
        try:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                if line.startswith("Q0:"):
                    final_quat_count += 1
                    if final_quat_count <= 3:
                        print(f"✓ QUAT #{final_quat_count}: {line}")
                elif line.startswith("[CAL]"):
                    print(f"✓ {line}")
                elif line.startswith("RAW"):
                    print(f"⚠ Still sending RAW: {line}")
        except Exception as e:
            pass
    time.sleep(0.01)

ser.close()

# Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"RAW data lines received: {raw_count}")
print(f"Quaternion lines during RAW mode: {quat_count}")
print(f"Quaternion lines after disable: {final_quat_count}")
print(f"Errors: {error_count}")

if raw_count >= 50:
    print("\n✓ SUCCESS: Sensor is sending RAW data in calibration mode")
    print("  Calibration data collection should work properly")
elif raw_count > 0:
    print(f"\n⚠ WARNING: Only received {raw_count} RAW samples (expected ~200)")
    print("  Sensor may be slow or connection unstable")
else:
    print("\n❌ FAILED: No RAW data received!")
    print("  Problem: Firmware may not be responding to CAL_START command")
    print("  Solution: Re-flash the firmware with PlatformIO")

print("\n" + "=" * 70)
