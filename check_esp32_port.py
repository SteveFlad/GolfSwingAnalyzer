"""Check if ESP32 is connected to COM11 and read basic info"""
import serial
import serial.tools.list_ports

def check_port():
    # List all available ports
    print("Available COM ports:")
    ports = serial.tools.list_ports.comports()
    for port in ports:
        print(f"  {port.device}: {port.description}")
        if "USB" in port.description or "Serial" in port.description:
            print(f"    Hardware ID: {port.hwid}")
    
    # Try to connect to COM11
    print("\nTrying to connect to COM11...")
    try:
        ser = serial.Serial('COM11', 115200, timeout=2)
        print(f"✓ Successfully opened COM11")
        print(f"  Baudrate: {ser.baudrate}")
        print(f"  Port: {ser.port}")
        
        # Try to read some data
        print("\nListening for data (2 seconds)...")
        ser.reset_input_buffer()
        data = ser.read(100)
        if data:
            print(f"Received {len(data)} bytes:")
            try:
                print(data.decode('utf-8', errors='ignore'))
            except:
                print(data)
        else:
            print("No data received (device may be idle or not outputting)")
        
        ser.close()
        print("\n✓ COM11 is accessible and responding")
        return True
        
    except serial.SerialException as e:
        print(f"✗ Error opening COM11: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    check_port()
