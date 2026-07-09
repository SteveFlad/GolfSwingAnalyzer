"""Find XIAO-ESP32-S3 USB connection"""
import serial.tools.list_ports

print("Searching for ESP32 devices...\n")

found = False
for port in serial.tools.list_ports.comports():
    print(f"Port: {port.device}")
    print(f"  Description: {port.description}")
    print(f"  Hardware ID: {port.hwid}")
    
    # Look for ESP32 or USB UART bridges commonly used with ESP32
    if any(keyword in port.description.upper() for keyword in ['USB', 'UART', 'SERIAL']) \
       and 'BLUETOOTH' not in port.description.upper():
        print(f"  ⭐ Possible ESP32 device!")
        found = True
    print()

if not found:
    print("❌ No USB serial devices found.")
    print("\nMake sure:")
    print("  1. XIAO-ESP32-S3 is connected via USB-C cable")
    print("  2. Cable supports data transfer (not charge-only)")
    print("  3. Drivers are installed (should be automatic on Windows)")
else:
    print("\n✓ Found potential ESP32 device(s) above")
    print("\nTo read flash, use:")
    print("  .venv\\Scripts\\python.exe -m esptool --port COMX read_flash 0x0 0x800000 flash_dump.bin")
