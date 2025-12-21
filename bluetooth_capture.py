"""
Bluetooth Communication Module
Handles reading quaternion data from ESP32 via Bluetooth
"""

import threading
import time
import re


class BluetoothCapture:
    def __init__(self, device_name=None, device_address=None, callback=None, connection_lost_callback=None):
        """
        Initialize Bluetooth capture
        device_name: Bluetooth device name (e.g., 'GolfSwingAnalyzer')
        device_address: Bluetooth MAC address (e.g., 'XX:XX:XX:XX:XX:XX')
        callback: Function to call when new data is received
        connection_lost_callback: Function to call when connection is lost
        """
        self.device_name = device_name
        self.device_address = device_address
        self.callback = callback
        self.connection_lost_callback = connection_lost_callback
        self.bt_socket = None
        self.running = False
        self.thread = None
        
        # Connection monitoring
        self.last_data_time = None
        self.data_timeout = 5.0
        self.total_received = 0
        self.total_parsed = 0
        
        # Regex pattern to match quaternion data
        self.pattern = re.compile(r'Q0:([-+]?\d*\.?\d+)\s+Q1:([-+]?\d*\.?\d+)\s+Q2:([-+]?\d*\.?\d+)\s+Q3:([-+]?\d*\.?\d+)')
        
    def start(self):
        """Start Bluetooth communication"""
        try:
            import bluetooth
            
            # Find the device if only name is provided
            if self.device_name and not self.device_address:
                print(f"Searching for Bluetooth device '{self.device_name}'...")
                nearby_devices = bluetooth.discover_devices(lookup_names=True, duration=8)
                
                for addr, name in nearby_devices:
                    if self.device_name.lower() in name.lower():
                        self.device_address = addr
                        print(f"Found device: {name} at {addr}")
                        break
                
                if not self.device_address:
                    raise Exception(f"Could not find Bluetooth device '{self.device_name}'")
            
            if not self.device_address:
                raise Exception("No device address or name provided")
            
            # Connect to the device
            print(f"Connecting to {self.device_address}...")
            
            # Try to find the Serial Port Profile (SPP) service
            services = bluetooth.find_service(address=self.device_address)
            
            if not services:
                # Try standard SPP port
                port = 1
            else:
                # Use the first available service port
                port = services[0]["port"]
            
            self.bt_socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            self.bt_socket.connect((self.device_address, port))
            
            time.sleep(2)  # Wait for connection to stabilize
            
            self.running = True
            self.last_data_time = time.time()
            self.total_received = 0
            self.total_parsed = 0
            
            self.thread = threading.Thread(target=self._read_loop, daemon=True)
            self.thread.start()
            
            print(f"Connected to Bluetooth device {self.device_address}")
            
        except ImportError:
            raise Exception("PyBluez library not installed. Install with: pip install pybluez")
        except Exception as e:
            raise Exception(f"Failed to connect via Bluetooth: {e}")
    
    def stop(self):
        """Stop Bluetooth communication"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        if self.bt_socket:
            try:
                self.bt_socket.close()
            except:
                pass
            print("Bluetooth connection closed")
    
    def is_connected(self):
        """Check if Bluetooth connection is active"""
        return self.bt_socket is not None and self.running
    
    def get_stats(self):
        """Get connection statistics"""
        return {
            'total_received': self.total_received,
            'total_parsed': self.total_parsed,
            'parse_rate': (self.total_parsed / self.total_received * 100) if self.total_received > 0 else 0,
            'last_data_time': self.last_data_time,
            'seconds_since_data': (time.time() - self.last_data_time) if self.last_data_time else None
        }
    
    def _read_loop(self):
        """Main reading loop (runs in separate thread)"""
        line_count = 0
        last_timeout_check = time.time()
        buffer = ""
        
        while self.running:
            try:
                # Check for data timeout
                current_time = time.time()
                if current_time - last_timeout_check > 1.0:
                    last_timeout_check = current_time
                    if self.last_data_time and (current_time - self.last_data_time) > self.data_timeout:
                        print(f"[WARNING] No data received for {self.data_timeout} seconds")
                        print(f"Total received: {self.total_received}, Parsed: {self.total_parsed}")
                        if self.connection_lost_callback:
                            self.connection_lost_callback("Data timeout - no data received")
                        self.running = False
                        break
                
                if self.bt_socket:
                    try:
                        # Read data from Bluetooth socket
                        data = self.bt_socket.recv(1024).decode('utf-8', errors='ignore')
                        
                        if data:
                            buffer += data
                            
                            # Process complete lines
                            while '\n' in buffer:
                                line, buffer = buffer.split('\n', 1)
                                line = line.strip()
                                
                                if line:
                                    line_count += 1
                                    self.total_received += 1
                                    self.last_data_time = time.time()
                                    
                                    # Print first few lines and periodic debug info
                                    if line_count <= 10 or line_count % 50 == 0:
                                        print(f"[BT DEBUG] Received line {line_count}: {line}")
                                    
                                    parsed_data = self._parse_line(line)
                                    if parsed_data:
                                        self.total_parsed += 1
                                        if self.callback:
                                            self.callback(parsed_data)
                                    elif line and not parsed_data:
                                        if line_count % 100 == 0:
                                            print(f"[BT DEBUG] Could not parse line: {line}")
                        else:
                            time.sleep(0.01)
                            
                    except Exception as e:
                        print(f"[ERROR] Bluetooth read error: {e}")
                        if self.connection_lost_callback:
                            self.connection_lost_callback(f"Bluetooth error: {e}")
                        self.running = False
                        break
                else:
                    print("[ERROR] Bluetooth connection lost")
                    if self.connection_lost_callback:
                        self.connection_lost_callback("Bluetooth socket closed")
                    self.running = False
                    break
                    
            except Exception as e:
                print(f"[ERROR] Error in read loop: {e}")
                time.sleep(0.01)
        
        print(f"Bluetooth read loop ended. Total received: {self.total_received}, Parsed: {self.total_parsed}")
    
    def _parse_line(self, line):
        """Parse a line of quaternion data"""
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


def discover_devices(duration=8):
    """
    Discover nearby Bluetooth devices
    Returns list of (address, name) tuples
    """
    try:
        import bluetooth
        print(f"Scanning for Bluetooth devices (this may take {duration} seconds)...")
        nearby_devices = bluetooth.discover_devices(lookup_names=True, duration=duration)
        return nearby_devices
    except ImportError:
        raise Exception("PyBluez library not installed. Install with: pip install pybluez")
    except Exception as e:
        raise Exception(f"Bluetooth scan failed: {e}")


# Test function
if __name__ == "__main__":
    def test_callback(data):
        print(f"Received: Q0={data['q0']:.3f}, Q1={data['q1']:.3f}, Q2={data['q2']:.3f}, Q3={data['q3']:.3f}")
    
    print("Discovering Bluetooth devices...")
    try:
        devices = discover_devices()
        print(f"\nFound {len(devices)} device(s):")
        for addr, name in devices:
            print(f"  {name} - {addr}")
        
        if devices:
            # You can test connection to a specific device
            # Uncomment and modify this section:
            # device_addr = devices[0][0]
            # capture = BluetoothCapture(device_address=device_addr, callback=test_callback)
            # capture.start()
            # 
            # while True:
            #     time.sleep(0.1)
            pass
            
    except KeyboardInterrupt:
        print("\nStopping...")
    except Exception as e:
        print(f"Error: {e}")
