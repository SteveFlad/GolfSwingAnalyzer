"""
BLE Data Capture Module for Golf Swing Analyzer

This module provides BLE (Bluetooth Low Energy) communication for receiving 
quaternion data from the XIAO ESP32S3 golf swing analyzer device.

Uses the bleak library for cross-platform BLE support.
"""

import asyncio
import threading
import time
import re
from typing import Optional, Callable
from dataclasses import dataclass

try:
    from bleak import BleakClient, BleakScanner
    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False
    print("Warning: bleak not installed. BLE functionality will be disabled.")
    print("Install with: pip install bleak")

@dataclass
class BLEDeviceInfo:
    """Information about a discovered BLE device"""
    name: str
    address: str
    rssi: int = 0


class BLECapture:
    """BLE data capture with similar interface to SerialCapture"""
    
    # BLE UUIDs matching ESP32 firmware
    SERVICE_UUID = "12345678-1234-1234-1234-123456789abc"
    CHARACTERISTIC_UUID = "87654321-4321-4321-4321-cba987654321"
    
    def __init__(self, 
                 device_address: str,
                 data_callback: Optional[Callable[[tuple], None]] = None,
                 connection_lost_callback: Optional[Callable[[], None]] = None):
        """
        Initialize BLE capture
        
        Args:
            device_address: BLE device address (MAC address on Windows/Linux)
            data_callback: Callback function(quaternion_tuple) called when quaternion data received
            connection_lost_callback: Callback function() called when connection is lost
        """
        self.device_address = device_address
        self.data_callback = data_callback
        self.connection_lost_callback = connection_lost_callback
        
        self.client: Optional[BleakClient] = None
        self.is_running = False
        self.asyncio_loop = None
        self.asyncio_thread = None
        
        # Statistics
        self.total_received = 0
        self.total_parsed = 0
        self.last_data_time = None
        self.data_timeout = 5.0  # seconds
        
        # Latest data storage for calibration
        self.latest_raw_data = None
        self.calibration_mode = False
        
        # Pattern for quaternion data: Q0:w Q1:x Q2:y Q3:z
        self.quaternion_pattern = re.compile(r'Q0:([-\d.]+)\s+Q1:([-\d.]+)\s+Q2:([-\d.]+)\s+Q3:([-\d.]+)')
        
        # Pattern for raw sensor data: RAW AX:x.xx AY:y.yy AZ:z.zz GX:x.xx GY:y.yy GZ:z.zz
        self.raw_pattern = re.compile(
            r'RAW\s+AX:([-+]?\d*\.?\d+)\s+AY:([-+]?\d*\.?\d+)\s+AZ:([-+]?\d*\.?\d+)\s+' +
            r'GX:([-+]?\d*\.?\d+)\s+GY:([-+]?\d*\.?\d+)\s+GZ:([-+]?\d*\.?\d+)'
        )
    
    @staticmethod
    async def scan_devices(timeout: float = 5.0) -> list[BLEDeviceInfo]:
        """
        Scan for BLE devices
        
        Args:
            timeout: Scan duration in seconds
            
        Returns:
            List of BLEDeviceInfo objects
        """
        if not BLEAK_AVAILABLE:
            return []
        
        devices = await BleakScanner.discover(timeout=timeout)
        result = []
        
        for device in devices:
            name = device.name or "Unknown"
            address = device.address
            rssi = getattr(device, 'rssi', 0)
            
            result.append(BLEDeviceInfo(name=name, address=address, rssi=rssi))
        
        return result
    
    def start(self):
        """Start BLE data capture in background thread"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start asyncio event loop in separate thread
        self.asyncio_thread = threading.Thread(target=self._run_asyncio_loop, daemon=True)
        self.asyncio_thread.start()
        
        # Wait for loop to be ready
        while self.asyncio_loop is None:
            time.sleep(0.01)
    
    def _run_asyncio_loop(self):
        """Run asyncio event loop in separate thread"""
        self.asyncio_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.asyncio_loop)
        
        try:
            self.asyncio_loop.run_until_complete(self._connect_and_read())
        except Exception as e:
            print(f"BLE error: {e}")
        finally:
            self.asyncio_loop.close()
            self.asyncio_loop = None
    
    async def _connect_and_read(self):
        """Connect to device and start reading data"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print(f"BLE connection retry {attempt}/{max_retries}...")
                    await asyncio.sleep(retry_delay)
                
                print(f"Connecting to BLE device {self.device_address}...")
                self.client = BleakClient(self.device_address, timeout=20.0)
                await self.client.connect(timeout=20.0)
                
                # Give device time to stabilize
                await asyncio.sleep(0.5)
                
                # Verify service and characteristic exist
                services = self.client.services
                service_found = False
                char_found = False
                
                for service in services:
                    if service.uuid.lower() == self.SERVICE_UUID.lower():
                        service_found = True
                        for char in service.characteristics:
                            if char.uuid.lower() == self.CHARACTERISTIC_UUID.lower():
                                char_found = True
                                break
                        break
                
                if not service_found or not char_found:
                    await self.client.disconnect()
                    print(f"ERROR: Device doesn't have required BLE service/characteristic")
                    if self.connection_lost_callback:
                        self.connection_lost_callback()
                    return
                
                # Subscribe to notifications
                await self.client.start_notify(self.CHARACTERISTIC_UUID, self._notification_handler)
                
                print("BLE connected and receiving data")
                self.last_data_time = time.time()
                
                # Keep connection alive and monitor timeout
                while self.is_running and self.client.is_connected:
                    await asyncio.sleep(0.5)
                    
                    # Check for data timeout
                    if self.last_data_time:
                        time_since_data = time.time() - self.last_data_time
                        if time_since_data > self.data_timeout:
                            print(f"BLE data timeout ({time_since_data:.1f}s)")
                            break
                
                # Disconnect
                if self.client.is_connected:
                    await self.client.stop_notify(self.CHARACTERISTIC_UUID)
                    await self.client.disconnect()
                
                break  # Success, exit retry loop
                
            except Exception as e:
                print(f"BLE connection attempt {attempt + 1} failed: {e}")
                if self.client:
                    try:
                        await self.client.disconnect()
                    except:
                        pass
                
                if attempt == max_retries - 1:
                    print(f"BLE connection failed after {max_retries} attempts")
                    if self.connection_lost_callback:
                        self.connection_lost_callback()
        
        # Connection lost or stopped
        if self.connection_lost_callback and self.is_running:
            self.connection_lost_callback()
    
    def _notification_handler(self, sender, data: bytearray):
        """Handle BLE characteristic notifications"""
        try:
            message = data.decode('utf-8', errors='ignore').strip()
            self.total_received += 1
            self.last_data_time = time.time()
            
            # Try to parse raw sensor data first
            raw_match = self.raw_pattern.search(message)
            if raw_match:
                ax = float(raw_match.group(1))
                ay = float(raw_match.group(2))
                az = float(raw_match.group(3))
                gx = float(raw_match.group(4))
                gy = float(raw_match.group(5))
                gz = float(raw_match.group(6))
                
                self.total_parsed += 1
                
                # Store for calibration access
                self.latest_raw_data = {
                    'accel': [ax, ay, az],
                    'gyro': [gx, gy, gz],
                    'timestamp': time.time(),
                    'type': 'raw'
                }
                
                if self.data_callback:
                    self.data_callback(self.latest_raw_data)
                
                return
            
            # Try to parse quaternion data
            match = self.quaternion_pattern.search(message)
            if match:
                q0 = float(match.group(1))
                q1 = float(match.group(2))
                q2 = float(match.group(3))
                q3 = float(match.group(4))
                
                self.total_parsed += 1
                
                if self.data_callback:
                    self.data_callback((q0, q1, q2, q3))
            
        except Exception as e:
            print(f"BLE notification error: {e}")
    
    def is_connected(self):
        """Check if BLE is connected"""
        return self.is_running and self.client is not None and (self.client.is_connected if hasattr(self.client, 'is_connected') else False)
    
    def stop(self):
        """Stop BLE capture"""
        self.is_running = False
        
        # Give time for graceful shutdown
        if self.asyncio_thread:
            self.asyncio_thread.join(timeout=2.0)
    
    def get_stats(self):
        """Get capture statistics"""
        parse_rate = 0.0
        if self.total_received > 0:
            parse_rate = (self.total_parsed / self.total_received) * 100
        
        return {
            'total_received': self.total_received,
            'total_parsed': self.total_parsed,
            'parse_rate': parse_rate
        }
    
    def enable_calibration_mode(self):
        """Enable calibration mode to receive raw sensor data"""
        if self.is_connected() and self.client:
            self.calibration_mode = True
            # Send command via BLE write
            asyncio.run_coroutine_threadsafe(
                self.client.write_gatt_char(self.CHARACTERISTIC_UUID, b"CAL_START"),
                self.asyncio_loop
            )
            print("BLE: Calibration mode enabled")
            return True
        return False
    
    def disable_calibration_mode(self):
        """Disable calibration mode to receive quaternion data"""
        if self.is_connected() and self.client:
            self.calibration_mode = False
            # Send command via BLE write
            asyncio.run_coroutine_threadsafe(
                self.client.write_gatt_char(self.CHARACTERISTIC_UUID, b"CAL_STOP"),
                self.asyncio_loop
            )
            print("BLE: Calibration mode disabled")
            return True
        return False
    
    def get_latest_raw_data(self):
        """Get the most recent raw sensor data (for calibration)"""
        return self.latest_raw_data


# Synchronous wrapper for device scanning
def scan_ble_devices_sync(timeout: float = 5.0) -> list[BLEDeviceInfo]:
    """
    Synchronous wrapper for scanning BLE devices
    
    Args:
        timeout: Scan duration in seconds
        
    Returns:
        List of BLEDeviceInfo objects
    """
    if not BLEAK_AVAILABLE:
        return []
    
    # Run in new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(BLECapture.scan_devices(timeout))
    finally:
        loop.close()


# Example usage
if __name__ == "__main__":
    print("Scanning for BLE devices...")
    devices = scan_ble_devices_sync(timeout=5.0)
    
    if not devices:
        print("No devices found")
    else:
        print(f"\nFound {len(devices)} device(s):")
        for i, device in enumerate(devices, 1):
            print(f"  {i}. {device.name} ({device.address}) RSSI: {device.rssi} dBm")
            
            if "XIAO" in device.name.upper() or "ESP32" in device.name.upper():
                print(f"     ^ This looks like an ESP32 device!")
    
    # Example: Connect to first ESP32 device found
    esp32_devices = [d for d in devices if "XIAO" in d.name.upper() or "ESP32" in d.name.upper()]
    
    if esp32_devices:
        print(f"\nConnecting to {esp32_devices[0].name}...")
        
        def on_data(quat):
            print(f"Quaternion: {quat}")
        
        def on_disconnect():
            print("Connection lost!")
        
        capture = BLECapture(esp32_devices[0].address, on_data, on_disconnect)
        
        try:
            capture.start()
            
            # Run for 10 seconds
            time.sleep(10)
            
            stats = capture.get_stats()
            print(f"\nStats: {stats}")
            
        finally:
            capture.stop()
