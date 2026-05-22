"""
Serial Communication Module
Handles reading quaternion data from ESP32 via serial port
"""

import re
import threading
import time

import serial


class SerialCapture:
    def __init__(self, port, baudrate=115200, callback=None, connection_lost_callback=None):
        """
        Initialize serial capture
        port: COM port name (e.g., 'COM3')
        baudrate: Serial baudrate (default 115200)
        callback: Function to call when new data is received
        connection_lost_callback: Function to call when connection is lost
        """
        self.port = port
        self.baudrate = baudrate
        self.callback = callback
        self.connection_lost_callback = connection_lost_callback
        self.serial_conn = None
        self.running = False
        self.thread = None
        
        # Connection monitoring
        self.last_data_time = None
        self.data_timeout = 5.0  # Seconds without data before considering connection lost
        self.total_received = 0
        self.total_parsed = 0
        
        # Latest data storage for calibration
        self.latest_raw_data = None
        self.calibration_mode = False
        
        # Regex pattern to match quaternion data: Q0:0.123 Q1:-0.456 Q2:0.789 Q3:-0.012
        self.pattern = re.compile(r'Q0:([-+]?\d*\.?\d+)\s+Q1:([-+]?\d*\.?\d+)\s+Q2:([-+]?\d*\.?\d+)\s+Q3:([-+]?\d*\.?\d+)')
        
        # Regex pattern to match raw sensor data: RAW AX:1.23 AY:-4.56 AZ:9.81 GX:0.12 GY:-0.34 GZ:0.56
        self.raw_pattern = re.compile(
            r'RAW\s+AX:([-+]?\d*\.?\d+)\s+AY:([-+]?\d*\.?\d+)\s+AZ:([-+]?\d*\.?\d+)\s+' +
            r'GX:([-+]?\d*\.?\d+)\s+GY:([-+]?\d*\.?\d+)\s+GZ:([-+]?\d*\.?\d+)'
        )
        self.raw_data_received_count = 0
        
    def start(self):
        """Start serial communication"""
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            time.sleep(2)  # Wait for connection to stabilize
            self.running = True
            self.last_data_time = time.time()
            self.total_received = 0
            self.total_parsed = 0
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
        return self.serial_conn is not None and self.serial_conn.is_open and self.running
    
    def get_stats(self):
        """Get connection statistics"""
        return {
            'total_received': self.total_received,
            'total_parsed': self.total_parsed,
            'parse_rate': (self.total_parsed / self.total_received * 100) if self.total_received > 0 else 0,
            'last_data_time': self.last_data_time,
            'seconds_since_data': (time.time() - self.last_data_time) if self.last_data_time else None
        }
    
    def enable_calibration_mode(self):
        """Enable calibration mode to receive raw sensor data"""
        if self.serial_conn and self.serial_conn.is_open:
            self.calibration_mode = True
            self.latest_raw_data = None  # Clear old data
            self.raw_data_received_count = 0
            self.serial_conn.write(b"CAL_START\n")
            self.serial_conn.flush()  # Ensure command is sent immediately
            print("[CAL DEBUG] Calibration mode enabled - CAL_START command sent")
            time.sleep(0.1)  # Give firmware time to respond
            return True
        print("[CAL DEBUG] Could not enable calibration - serial not open")
        return False
    
    def disable_calibration_mode(self):
        """Disable calibration mode to receive quaternion data"""
        if self.serial_conn and self.serial_conn.is_open:
            self.calibration_mode = False
            self.serial_conn.write(b"CAL_STOP\n")
            print("Calibration mode disabled")
            return True
        return False
    
    def get_latest_raw_data(self):
        """Get the most recent raw sensor data (for calibration)"""
        return self.latest_raw_data
        
    def _read_loop(self):
        """Main reading loop (runs in separate thread)"""
        line_count = 0
        last_timeout_check = time.time()
        
        while self.running:
            try:
                # Check for data timeout (connection still open but no data flowing)
                current_time = time.time()
                if current_time - last_timeout_check > 1.0:  # Check every second
                    last_timeout_check = current_time
                    if self.last_data_time and (current_time - self.last_data_time) > self.data_timeout:
                        print(f"[WARNING] No data received for {self.data_timeout} seconds")
                        print(f"Total received: {self.total_received}, Parsed: {self.total_parsed}")
                        if self.connection_lost_callback:
                            self.connection_lost_callback("Data timeout - no data received")
                        self.running = False
                        break
                
                if self.serial_conn and self.serial_conn.is_open:
                    if self.serial_conn.in_waiting > 0:
                        line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                        
                        if line:
                            line_count += 1
                            self.total_received += 1
                            self.last_data_time = time.time()  # Update heartbeat
                            
                            # Print first few lines and periodic debug info
                            if line_count <= 10 or line_count % 50 == 0:
                                print(f"[DEBUG] Received line {line_count}: {line}")
                            
                            # Always print RAW lines during calibration
                            if self.calibration_mode and line.startswith("RAW"):
                                print(f"[CAL DEBUG] RAW line received: {line}")
                            
                            data = self._parse_line(line)
                            if data:
                                self.total_parsed += 1
                                if self.callback:
                                    self.callback(data)
                            elif line and not data:
                                # Log unparsed lines occasionally for debugging
                                if line_count % 100 == 0:
                                    print(f"[DEBUG] Could not parse line: {line}")
                    else:
                        # Small delay when no data available to prevent CPU spinning
                        time.sleep(0.01)
                else:
                    print("[ERROR] Serial connection lost - port closed")
                    if self.connection_lost_callback:
                        self.connection_lost_callback("Serial port closed")
                    self.running = False
                    break
                            
            except serial.SerialException as e:
                print(f"[ERROR] Serial error: {e}")
                if self.connection_lost_callback:
                    self.connection_lost_callback(f"Serial error: {e}")
                self.running = False
                break
            except Exception as e:
                print(f"[ERROR] Error reading data: {e}")
                # Don't break on general exceptions, just log and continue
                time.sleep(0.01)
                
        print(f"Read loop ended. Total received: {self.total_received}, Parsed: {self.total_parsed}")
        
    def _parse_line(self, line):
        """
        Parse a line of quaternion or raw sensor data
        Expected formats:
        - Quaternion: Q0:0.123 Q1:-0.456 Q2:0.789 Q3:-0.012
        - Raw sensor: RAW AX:1.23 AY:-4.56 AZ:9.81 GX:0.12 GY:-0.34 GZ:0.56
        - Error: ERROR:SENSOR_DISCONNECTED
        - Status: STATUS:SENSOR_RESTORED
        """
        # Check for error/status messages from firmware
        if line.startswith("ERROR:"):
            error_msg = line.replace("ERROR:", "").replace("_", " ")
            print(f"[SERIAL ERROR] Sensor error: {error_msg}")
            if self.connection_lost_callback:
                self.connection_lost_callback(f"Sensor error: {error_msg}")
            return None
        
        if line.startswith("STATUS:"):
            status_msg = line.replace("STATUS:", "").replace("_", " ")
            print(f"[SERIAL STATUS] {status_msg}")
            return None
        
        # Try to parse raw sensor data first
        raw_match = self.raw_pattern.search(line)
        if raw_match:
            self.raw_data_received_count += 1
            if self.raw_data_received_count <= 5:
                print(f"[CAL DEBUG] Successfully matched RAW line #{self.raw_data_received_count}: {line}")
            try:
                ax = float(raw_match.group(1))
                ay = float(raw_match.group(2))
                az = float(raw_match.group(3))
                gx = float(raw_match.group(4))
                gy = float(raw_match.group(5))
                gz = float(raw_match.group(6))
                
                data = {
                    'accel': [ax, ay, az],
                    'gyro': [gx, gy, gz],
                    'timestamp': time.time(),
                    'raw': line,
                    'type': 'raw'
                }
                
                # Store for calibration access
                self.latest_raw_data = data
                
                return data
            except ValueError:
                return None
        elif self.calibration_mode and line.startswith("RAW"):
            print(f"[CAL DEBUG] RAW line did NOT match regex pattern: {line}")
            print(f"[CAL DEBUG] Expected pattern: RAW AX:# AY:# AZ:# GX:# GY:# GZ:#")
        
        # Try to parse quaternion data
        match = self.pattern.search(line)
        if match:
            try:
                q0 = float(match.group(1))
                q1 = float(match.group(2))
                q2 = float(match.group(3))
                q3 = float(match.group(4))
                
                data = {
                    'q0': q0,
                    'q1': q1,
                    'q2': q2,
                    'q3': q3,
                    'timestamp': time.time(),
                    'raw': line,
                    'type': 'quaternion'
                }
                
                # Store quaternion data too so get_latest_raw_data() returns current data
                self.latest_raw_data = data
                
                return data
            except ValueError:
                return None
        return None


# Test function
if __name__ == "__main__":
    def test_callback(data):
        print(f"Received: Q0={data['q0']:.3f}, Q1={data['q1']:.3f}, Q2={data['q2']:.3f}, Q3={data['q3']:.3f}")
    
    # You'll need to change this to your actual COM port
    TEST_PORT = "COM10"
    
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
