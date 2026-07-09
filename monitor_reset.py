import serial
import time

PORT = 'COM3'
BAUD = 115200

print(f"Monitoring {PORT} at {BAUD} baud")
print("Press the RESET button on your ESP32 NOW and watch for startup messages...")
print("-" * 60)

try:
    with serial.Serial(PORT, BAUD, timeout=1) as ser:
        time.sleep(0.5)
        ser.reset_input_buffer()
        
        for i in range(50):  # Monitor for 10 seconds
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                try:
                    print(data.decode('utf-8'), end='')
                except:
                    print(f"[Binary: {data.hex()}]")
            time.sleep(0.2)
            
except Exception as e:
    print(f"Error: {e}")
