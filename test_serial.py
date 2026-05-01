"""
Simple serial monitor to test if data is coming from the device
This will print everything received from the serial port
"""

import sys

import serial
import serial.tools.list_ports

def list_ports():
    """List all available serial ports"""
    ports = serial.tools.list_ports.comports()
    print("\nAvailable Serial Ports:")
    print("-" * 50)
    for i, port in enumerate(ports):
        print(f"{i+1}. {port.device} - {port.description}")
    print("-" * 50)
    return [port.device for port in ports]

def monitor_serial(port, baudrate=115200):
    """Monitor serial port and print all incoming data"""
    print(f"\nConnecting to {port} at {baudrate} baud...")
    
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        print(f"Connected! Monitoring data (Press Ctrl+C to stop)...\n")
        print("=" * 70)
        
        line_count = 0
        while True:
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        line_count += 1
                        print(f"[{line_count:04d}] {line}")
                except Exception as e:
                    print(f"Error reading line: {e}")
                    
    except serial.SerialException as e:
        print(f"Error: {e}")
        return False
    except KeyboardInterrupt:
        print("\n\nStopped by user")
        ser.close()
        print(f"Total lines received: {line_count}")
        return True
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == "__main__":
    available_ports = list_ports()
    
    if not available_ports:
        print("\nNo serial ports found!")
        sys.exit(1)
    
    # Use first port or let user specify
    if len(sys.argv) > 1:
        port = sys.argv[1]
    else:
        port = available_ports[0]
        print(f"\nUsing port: {port}")
        print("(You can specify a different port with: python test_serial.py COM#)")
    
    monitor_serial(port)
