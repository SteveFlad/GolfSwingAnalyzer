"""
Serial Communication Module
Handles reading quaternion data from ESP32 via serial port
"""

import serial
import threading
import time
import re


class SerialCapture:
    def __init__(self, port, baudrate=115200, callback=None):
        """
        Initialize serial capture
        port: COM port name (e.g., 'COM3')
        baudrate: Serial baudrate (default 115200)
        callback: Function to call when new data is received
        """
        self.port = port
        self.baudrate = baudrate
        self.callback = callback
        self.serial_conn = None
        self.running = False
        self.thread = None
        
        # Regex pattern to match quaternion data: Q0:0.123 Q1:-0.456 Q2:0.789 Q3:-0.012
        self.pattern = re.compile(r'Q0:([-+]?\d*\.?\d+)\s+Q1:([-+]?\d*\.?\d+)\s+Q2:([-+]?\d*\.?\d+)\s+Q3:([-+]?\d*\.?\d+)')
        
    def start(self):
        """Start serial communication"""
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            time.sleep(2)  # Wait for connection to stabilize
            self.running = True
            self.thread = threading.Thread(target=self._read_loop, daemon=True)
            self.thread.start()
            print(f"Connected to {self.port} at {self.baudrate} baud")
        except serial.SerialException as e:
            raise Exception(f"Failed to connect to {self.port}: {e}")
            
    def stop(self):
        """Stop serial communication"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            print("Serial connection closed")
            
    def is_connected(self):
        """Check if serial connection is active"""
        return self.serial_conn is not None and self.serial_conn.is_open
        
    def _read_loop(self):
        """Main reading loop (runs in separate thread)"""
        while self.running:
            try:
                if self.serial_conn.in_waiting > 0:
                    line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    
                    if line:
                        data = self._parse_line(line)
                        if data and self.callback:
                            self.callback(data)
                            
            except serial.SerialException as e:
                print(f"Serial error: {e}")
                break
            except Exception as e:
                print(f"Error reading data: {e}")
                
        print("Read loop ended")
        
    def _parse_line(self, line):
        """
        Parse a line of quaternion data
        Expected format: Q0:0.123 Q1:-0.456 Q2:0.789 Q3:-0.012
        """
        match = self.pattern.search(line)
        if match:
            try:
                q0 = float(match.group(1))
                q1 = float(match.group(2))
                q2 = float(match.group(3))
                q3 = float(match.group(4))
                
                return {
                    'q0': q0,
                    'q1': q1,
                    'q2': q2,
                    'q3': q3,
                    'timestamp': time.time(),
                    'raw': line
                }
            except ValueError:
                return None
        return None


# Test function
if __name__ == "__main__":
    def test_callback(data):
        print(f"Received: Q0={data['q0']:.3f}, Q1={data['q1']:.3f}, Q2={data['q2']:.3f}, Q3={data['q3']:.3f}")
    
    # You'll need to change this to your actual COM port
    TEST_PORT = "COM3"
    
    print(f"Testing serial capture on {TEST_PORT}")
    print("Press Ctrl+C to stop")
    
    try:
        capture = SerialCapture(TEST_PORT, 115200, test_callback)
        capture.start()
        
        # Keep running until interrupted
        while True:
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nStopping...")
        capture.stop()
    except Exception as e:
        print(f"Error: {e}")
