"""
Bluetooth Communication Module for Windows
Uses native Windows Bluetooth support via socket module - no external dependencies!
"""

import socket
import threading
import time
import re


class BluetoothCapture:
    def __init__(self, device_name=None, device_address=None, callback=None, connection_lost_callback=None):
        """
        Initialize Bluetooth capture using Windows native Bluetooth
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
            if not self.device_address:
                raise Exception("Device address is required for Windows Bluetooth connection")
            
            # Normalize MAC address format (ensure colons, not dashes)
            self.device_address = self.device_address.replace('-', ':').upper()
            
            print(f"Connecting to {self.device_address} via Windows Bluetooth...")
            
            # Create Bluetooth socket using Windows native support
            # RFCOMM protocol (similar to serial port)
            self.bt_socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            
            # Set timeout for connection attempt
            self.bt_socket.settimeout(10)
            
            # Connect to device (channel 1 is standard for SPP)
            self.bt_socket.connect((self.device_address, 1))
            
            # Set to non-blocking after connection
            self.bt_socket.settimeout(1.0)
            
            time.sleep(2)  # Wait for connection to stabilize
            
            self.running = True
            self.last_data_time = time.time()
            self.total_received = 0
            self.total_parsed = 0
            
            self.thread = threading.Thread(target=self._read_loop, daemon=True)
            self.thread.start()
            
            print(f"Connected to Bluetooth device {self.device_address}")
            
        except socket.error as e:
            error_msg = str(e)
            if "10061" in error_msg:
                raise Exception(f"Connection refused. Make sure the device is paired and the firmware is running with Bluetooth enabled.")
            elif "10060" in error_msg:
                raise Exception(f"Connection timeout. Make sure the device is in range and powered on.")
            elif "10049" in error_msg:
                raise Exception(f"Invalid address. Check the MAC address format (XX:XX:XX:XX:XX:XX).")
            else:
                raise Exception(f"Bluetooth connection failed: {e}\n\nMake sure:\n1. Device is paired in Windows Bluetooth settings\n2. Device is not connected to another application\n3. Firmware has Bluetooth enabled")
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
                    
                    except socket.timeout:
                        # Timeout is normal, just means no data available
                        time.sleep(0.01)
                        continue
                        
                    except socket.error as e:
                        print(f"[ERROR] Bluetooth socket error: {e}")
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
    Discover nearby Bluetooth devices using Windows API
    Note: This requires the device to be already paired in Windows settings
    """
    try:
        import subprocess
        import re
        
        print(f"Scanning for paired Bluetooth devices...")
        
        # Use PowerShell to get paired Bluetooth devices
        ps_command = """
        Get-PnpDevice -Class Bluetooth | Where-Object {$_.Status -eq "OK"} | 
        Select-Object FriendlyName, InstanceId | 
        ForEach-Object {
            $name = $_.FriendlyName
            # Extract MAC from InstanceId (format varies)
            if ($_.InstanceId -match '([0-9A-F]{2}[_:]){5}[0-9A-F]{2}') {
                $mac = $matches[0] -replace '_', ':'
                Write-Output "$name|$mac"
            }
        }
        """
        
        result = subprocess.run(
            ["powershell", "-Command", ps_command],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        devices = []
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if '|' in line:
                    name, addr = line.strip().split('|', 1)
                    addr = addr.replace('_', ':').upper()
                    devices.append((addr, name))
        
        if not devices:
            print("\nNo paired devices found. Please pair your device in Windows Settings:")
            print("  Settings → Bluetooth & devices → Add device")
            print("\nNote: The device must be paired before it can be used.")
        
        return devices
        
    except Exception as e:
        raise Exception(f"Bluetooth scan failed: {e}\n\nTip: Make sure the device is paired in Windows Bluetooth settings first.")


# Test function
if __name__ == "__main__":
    def test_callback(data):
        print(f"Received: Q0={data['q0']:.3f}, Q1={data['q1']:.3f}, Q2={data['q2']:.3f}, Q3={data['q3']:.3f}")
    
    print("Discovering paired Bluetooth devices...")
    try:
        devices = discover_devices()
        print(f"\nFound {len(devices)} paired device(s):")
        for addr, name in devices:
            print(f"  {name} - {addr}")
        
        if devices:
            print("\nTo test connection, modify the code to use a specific device address")
            
    except KeyboardInterrupt:
        print("\nStopping...")
    except Exception as e:
        print(f"Error: {e}")
