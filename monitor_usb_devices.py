"""
Real-time USB Device Monitor
Watches for new devices being plugged in
"""
import serial.tools.list_ports
import time
import sys

print("=" * 70)
print("USB DEVICE MONITOR - Real-time Detection")
print("=" * 70)
print("\n📋 Scanning for current devices...\n")

def get_current_ports():
    """Get list of current port device IDs"""
    return {p.device: p for p in serial.tools.list_ports.comports()}

def get_usb_devices_wmic():
    """Use WMIC to get USB devices"""
    import subprocess
    try:
        result = subprocess.run(
            ['wmic', 'path', 'Win32_USBHub', 'get', 'DeviceID,Description', '/format:list'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout
    except:
        return None

# Initial scan
initial_ports = get_current_ports()
print(f"Currently connected serial ports ({len(initial_ports)}):")
for device, port in initial_ports.items():
    status = "📶 Bluetooth" if "BLUETOOTH" in port.description.upper() else "🔌 USB"
    print(f"  {status} {device}: {port.description}")

if not initial_ports:
    print("  (None)")

print("\n" + "=" * 70)
print("🔍 MONITORING FOR NEW DEVICES...")
print("=" * 70)
print("Instructions:")
print("  1. Leave this window open")
print("  2. Plug in your ESP32 via USB cable")
print("  3. Watch for detection messages below")
print("  4. Press Ctrl+C to stop monitoring")
print("\n" + "-" * 70 + "\n")

check_count = 0
try:
    while True:
        time.sleep(0.5)
        check_count += 1
        
        # Check every 0.5 seconds
        current_ports = get_current_ports()
        
        # Look for new devices
        new_devices = set(current_ports.keys()) - set(initial_ports.keys())
        removed_devices = set(initial_ports.keys()) - set(current_ports.keys())
        
        if new_devices:
            print(f"\n🎯 NEW DEVICE DETECTED! (scan #{check_count})")
            for device in new_devices:
                port = current_ports[device]
                print(f"\n  ✅ {device}")
                print(f"     Description: {port.description}")
                print(f"     Hardware ID: {port.hwid}")
                print(f"     Manufacturer: {port.manufacturer}")
                
                # Check if it's ESP32-like
                is_esp32 = False
                if 'VID:PID=10C4:EA60' in port.hwid.upper():
                    print(f"     🎯 CP2102 USB-UART - Common for ESP32!")
                    is_esp32 = True
                elif 'VID:PID=1A86:7523' in port.hwid.upper():
                    print(f"     🎯 CH340 USB-UART - Common for ESP32!")
                    is_esp32 = True
                elif 'VID:PID=303A' in port.hwid.upper():
                    print(f"     🎯 ESP32-S3 Native USB!")
                    is_esp32 = True
                elif 'VID:PID=2341' in port.hwid.upper():
                    print(f"     🎯 Arduino/Seeeduino device!")
                    is_esp32 = True
                elif any(x in port.description.upper() for x in ['CP210', 'CH340', 'USB-SERIAL']):
                    print(f"     🎯 USB-Serial adapter - Likely ESP32!")
                    is_esp32 = True
                
                if is_esp32:
                    print(f"\n     ⚡ THIS IS LIKELY YOUR ESP32!")
                    print(f"     To test connection, run:")
                    print(f"        .venv\\Scripts\\python.exe -m esptool --port {device} chip_id")
                
                # Try to open it
                try:
                    import serial
                    ser = serial.Serial(device, 115200, timeout=1)
                    print(f"     ✅ Successfully opened at 115200 baud")
                    ser.close()
                except Exception as e:
                    print(f"     ⚠️  Cannot open yet: {e}")
            
            initial_ports = current_ports
        
        if removed_devices:
            print(f"\n🔌 DEVICE REMOVED (scan #{check_count}):")
            for device in removed_devices:
                print(f"  ❌ {device}")
            initial_ports = current_ports
        
        # Print a dot every 10 checks to show it's still running
        if check_count % 10 == 0:
            print(f".", end="", flush=True)
            
except KeyboardInterrupt:
    print("\n\n" + "=" * 70)
    print("Monitoring stopped by user")
    print("=" * 70)
