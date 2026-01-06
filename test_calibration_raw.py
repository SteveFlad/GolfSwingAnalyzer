"""
Test script to verify calibration mode and RAW data reception
"""
import serial
import time

# Change this to your COM port
PORT = "COM4"
BAUD = 115200

print(f"Connecting to {PORT}...")
try:
    ser = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(2)  # Wait for connection
    print("Connected!")
    
    # Clear any pending data
    ser.reset_input_buffer()
    
    # Send CAL_START command
    print("\nSending CAL_START command...")
    ser.write(b"CAL_START\n")
    ser.flush()
    print("Command sent!")
    
    # Read responses for 5 seconds
    print("\nReading responses for 5 seconds...")
    start_time = time.time()
    line_count = 0
    raw_count = 0
    
    while time.time() - start_time < 5:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                line_count += 1
                print(f"Line {line_count}: {line}")
                if line.startswith("RAW"):
                    raw_count += 1
    
    print(f"\n--- Summary ---")
    print(f"Total lines received: {line_count}")
    print(f"RAW lines received: {raw_count}")
    
    # Send CAL_STOP
    print("\nSending CAL_STOP command...")
    ser.write(b"CAL_STOP\n")
    ser.flush()
    time.sleep(0.5)
    
    # Read any final responses
    while ser.in_waiting > 0:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if line:
            print(f"Final: {line}")
    
    ser.close()
    print("\nTest complete!")
    
except Exception as e:
    print(f"Error: {e}")
