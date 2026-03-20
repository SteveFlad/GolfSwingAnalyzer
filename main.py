"""
Golf Swing Analyzer - Main Application
Captures data from ICM-20948 sensor and visualizes 3D golf club path
"""

import sys
import threading
import json
import time
from datetime import datetime

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import serial.tools.list_ports

from serial_capture import SerialCapture
try:
    from ble_capture import BLECapture, scan_ble_devices_sync, BLEAK_AVAILABLE
    BLUETOOTH_AVAILABLE = BLEAK_AVAILABLE
    BLUETOOTH_TYPE = "BLE (Bluetooth Low Energy)" if BLEAK_AVAILABLE else None
except ImportError:
    BLUETOOTH_AVAILABLE = False
    BLECapture = None
    scan_ble_devices_sync = None
    BLUETOOTH_TYPE = None
from visualizer import SwingVisualizer
from sensor_calibration import SensorCalibration
from calibration_wizard import CalibrationWizard


class GolfSwingAnalyzer:
    def __init__(self, root):
        self.root = root
        self.root.title("Golf Swing Analyzer")
        self.root.state('zoomed')  # Maximize window
        
        self.serial_capture = None
        self.bluetooth_capture = None
        self.connection_type = None  # 'serial' or 'bluetooth'
        self.is_capturing = False
        self.current_data = []
        self.monitor_thread = None
        self.monitoring = False
        self.bt_devices = []
        
        # Initialize sensor calibration
        self.calibration = SensorCalibration('calibration_data.json')
        
        self.setup_ui()
        self.refresh_ports()
        
    def setup_ui(self):
        """Create the user interface"""
        # Control Frame
        control_frame = ttk.LabelFrame(self.root, text="Controls", padding=10)
        control_frame.pack(fill="x", padx=10, pady=5)
        
        # Connection Type Selection
        ttk.Label(control_frame, text="Connection:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.conn_type_var = tk.StringVar(value="serial")
        ttk.Radiobutton(control_frame, text="USB/Serial", variable=self.conn_type_var, 
                       value="serial", command=self.update_connection_ui).grid(row=0, column=1, sticky="w", padx=5)
        bt_radio = ttk.Radiobutton(control_frame, text="Bluetooth", variable=self.conn_type_var, 
                       value="bluetooth", command=self.update_connection_ui)
        bt_radio.grid(row=0, column=2, sticky="w", padx=5)
        if not BLUETOOTH_AVAILABLE:
            bt_radio.config(state="disabled")
        
        # Serial Port Selection
        ttk.Label(control_frame, text="Device:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(control_frame, textvariable=self.port_var, width=30)
        self.port_combo.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        
        ttk.Button(control_frame, text="Scan", command=self.scan_devices).grid(row=1, column=3, padx=5, pady=5)
        self.connect_btn = ttk.Button(control_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.grid(row=1, column=4, padx=5, pady=5)
        
        # Capture Controls
        ttk.Label(control_frame, text="Capture:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.capture_btn = tk.Button(control_frame, text="Start Capture", command=self.toggle_capture,
                         bg="green", fg="white", font=("Arial", 10, "bold"),
                         padx=10, pady=5)
        self.capture_btn.grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        
        ttk.Button(control_frame, text="Clear Data", command=self.clear_data).grid(row=2, column=3, padx=5, pady=5)
        
        # File Controls
        file_frame = ttk.LabelFrame(self.root, text="File Management", padding=10)
        file_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(file_frame, text="Save Data", command=self.save_data).pack(side="left", padx=5)
        ttk.Button(file_frame, text="Load Data", command=self.load_data).pack(side="left", padx=5)
        ttk.Button(file_frame, text="Visualize 3D", command=self.visualize_3d).pack(side="left", padx=5)
        
        # Calibration Controls
        calib_frame = ttk.LabelFrame(self.root, text="Sensor Calibration", padding=10)
        calib_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(calib_frame, text="Calibrate Sensor", command=self.start_calibration_wizard).pack(side="left", padx=5)
        ttk.Button(calib_frame, text="Reset Calibration", command=self.reset_calibration).pack(side="left", padx=5)
        
        self.calib_status_label = ttk.Label(calib_frame, text=f"Status: {self.calibration.get_calibration_status()}")
        self.calib_status_label.pack(side="left", padx=10)
        
        # Status Display
        status_frame = ttk.LabelFrame(self.root, text="Status", padding=10)
        status_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.status_text = tk.Text(status_frame, height=10, wrap="word")
        self.status_text.pack(fill="both", expand=True)
        scrollbar = ttk.Scrollbar(self.status_text)
        scrollbar.pack(side="right", fill="y")
        self.status_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.status_text.yview)
        
        # Log Bluetooth availability status
        if not BLUETOOTH_AVAILABLE:
            self.root.after(100, lambda: self.log_status(
                "Note: Bluetooth support not available. Using USB/Serial only. See README_BLUETOOTH.md for details."))
        elif BLUETOOTH_TYPE:
            self.root.after(100, lambda: self.log_status(
                f"Bluetooth support enabled ({BLUETOOTH_TYPE})"))
        
        # Data Summary
        summary_frame = ttk.LabelFrame(self.root, text="Data Summary", padding=10)
        summary_frame.pack(fill="x", padx=10, pady=5)
        
        self.data_count_label = ttk.Label(summary_frame, text="Data Points: 0")
        self.data_count_label.pack(side="left", padx=10)
        
        self.connection_label = ttk.Label(summary_frame, text="Status: Not Connected", foreground="red")
        self.connection_label.pack(side="left", padx=10)
        
    def update_connection_ui(self):
        """Update UI based on selected connection type"""
        conn_type = self.conn_type_var.get()
        if conn_type == "serial":
            self.refresh_ports()
        else:
            self.port_combo['values'] = [device[1] + " (" + device[0] + ")" for device in self.bt_devices]
            if not self.bt_devices:
                self.log_status("Click 'Scan' to discover Bluetooth devices")
    
    def scan_devices(self):
        """Scan for available devices based on connection type"""
        conn_type = self.conn_type_var.get()
        if conn_type == "serial":
            self.refresh_ports()
        else:
            self.scan_bluetooth()
    
    def refresh_ports(self):
        """Refresh available serial ports"""
        ports = serial.tools.list_ports.comports()
        # Filter out virtual Bluetooth COM ports (Windows creates these for legacy Bluetooth)
        filtered_ports = [p for p in ports if "Standard Serial over Bluetooth" not in p.description]
        port_list = [port.device for port in filtered_ports]
        self.port_combo['values'] = port_list
        if port_list:
            self.port_combo.current(0)
        self.log_status(f"Found {len(port_list)} serial port(s)")
    
    def scan_bluetooth(self):
        """Scan for BLE devices"""
        if not BLUETOOTH_AVAILABLE:
            messagebox.showerror("Bluetooth Not Available", 
                "BLE support requires the 'bleak' library.\n\n" +
                "Install with: pip install bleak\n\n" +
                "See README_BLUETOOTH.md for details.")
            return
        
        self.log_status(f"Scanning for BLE devices using {BLUETOOTH_TYPE}...")
        
        def scan_thread():
            try:
                devices = scan_ble_devices_sync(timeout=5.0)
                self.bt_devices = [(d.address, d.name) for d in devices]
                device_list = [d.name + " (" + d.address + ")" for d in devices]
                self.root.after(0, lambda: self.port_combo.config(values=device_list))
                if device_list:
                    self.root.after(0, lambda: self.port_combo.current(0))
                self.root.after(0, lambda: self.log_status(f"Found {len(devices)} BLE device(s)"))
            except Exception as e:
                self.root.after(0, lambda: self.log_status(f"BLE scan error: {e}"))
                self.root.after(0, lambda: messagebox.showerror("BLE Error", 
                    f"Failed to scan for BLE devices.\n\n{e}"))
        
        threading.Thread(target=scan_thread, daemon=True).start()
        
    def toggle_connection(self):
        """Toggle connection/disconnection"""
        if self.is_connected():
            self.disconnect()
        else:
            self.connect()
    
    def is_connected(self):
        """Check if any connection is active"""
        if self.serial_capture and self.serial_capture.is_connected():
            return True
        if self.bluetooth_capture and self.bluetooth_capture.is_connected():
            return True
        return False
    
    def connect(self):
        """Connect based on selected connection type"""
        conn_type = self.conn_type_var.get()
        if conn_type == "serial":
            self.connect_serial()
        else:
            self.connect_bluetooth()
    
    def disconnect(self):
        """Disconnect from current connection"""
        if self.connection_type == "serial":
            self.disconnect_serial()
        elif self.connection_type == "bluetooth":
            self.disconnect_bluetooth()
    
    def connect_serial(self):
        """Connect to selected serial port"""
        port = self.port_var.get()
        if not port:
            messagebox.showerror("Error", "Please select a serial port")
            return
            
        try:
            self.serial_capture = SerialCapture(port, 115200, self.on_data_received, self.on_connection_lost)
            self.serial_capture.start()
            self.connection_type = "serial"
            self.connection_label.config(text=f"Status: Connected to {port} (USB)", foreground="green")
            self.connect_btn.config(text="Disconnect")
            self.log_status(f"Connected to {port} via USB/Serial")
            self.start_monitoring()
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
            self.log_status(f"Connection failed: {e}")
    
    def connect_bluetooth(self):
        """Connect to selected BLE device"""
        if not BLUETOOTH_AVAILABLE:
            messagebox.showerror("BLE Not Available", 
                "BLE support requires the 'bleak' library.\nInstall with: pip install bleak")
            return
        
        selected = self.port_var.get()
        if not selected:
            messagebox.showerror("Error", "Please select a BLE device")
            return
        
        # Parse address from selection (format: "Name (XX:XX:XX:XX:XX:XX)")
        try:
            if '(' in selected and ')' in selected:
                device_addr = selected.split('(')[1].split(')')[0]
            else:
                device_addr = selected
            
            self.bluetooth_capture = BLECapture(
                device_address=device_addr,
                data_callback=self.on_data_received,
                connection_lost_callback=self.on_connection_lost
            )
            self.bluetooth_capture.start()
            self.connection_type = "bluetooth"
            self.connection_label.config(text=f"Status: Connected via BLE", foreground="green")
            self.connect_btn.config(text="Disconnect")
            self.log_status(f"Connected to {device_addr} via BLE")
            self.start_monitoring()
        except Exception as e:
            messagebox.showerror("BLE Error", str(e))
            self.log_status(f"BLE connection failed: {e}")
    
    def disconnect_serial(self):
        """Disconnect from serial port"""
        self.stop_monitoring()
        if self.serial_capture:
            self.serial_capture.stop()
            self.serial_capture = None
            self.connection_type = None
            self.connection_label.config(text="Status: Not Connected", foreground="red")
            self.connect_btn.config(text="Connect")
            self.log_status("Disconnected from USB/Serial")
    
    def disconnect_bluetooth(self):
        """Disconnect from BLE"""
        self.stop_monitoring()
        if self.bluetooth_capture:
            self.bluetooth_capture.stop()
            self.bluetooth_capture = None
            self.connection_type = None
            self.connection_label.config(text="Status: Not Connected", foreground="red")
            self.connect_btn.config(text="Connect")
            self.log_status("Disconnected from BLE")
    
    def toggle_capture(self):
        """Toggle capture on/off"""
        if self.is_capturing:
            # Stop capturing
            self.is_capturing = False
            self.capture_btn.config(text="Start Capture", bg="green")
            self.log_status(f"Capture stopped. Total data points: {len(self.current_data)}")
        else:
            # Start capturing
            if not self.is_connected():
                messagebox.showerror("Error", "Please connect to a device first")
                return
            
            self.is_capturing = True
            self.current_data = []
            self.capture_btn.config(text="Stop Capture", bg="red")
            self.log_status("Capture started")
        
    def clear_data(self):
        """Clear current data"""
        self.current_data = []
        self.update_data_count()
        self.log_status("Data cleared")
        
    def on_data_received(self, data):
        """Callback when new data is received from serial or BLE"""
        # Always log incoming data (even when not capturing) to verify data is being received
        if not hasattr(self, '_data_received_count'):
            self._data_received_count = 0
        self._data_received_count += 1
        
        # Handle both tuple (from BLE) and dict (from Serial) formats
        if isinstance(data, tuple) and len(data) == 4:
            # BLE sends tuple: (q0, q1, q2, q3)
            q0, q1, q2, q3 = data
            data_dict = {'q0': q0, 'q1': q1, 'q2': q2, 'q3': q3}
        elif isinstance(data, dict):
            # Serial sends dict
            data_dict = data
            
            # Check if this is raw sensor data (during calibration)
            if 'type' in data_dict and data_dict['type'] == 'raw':
                # Raw sensor data - just pass through, don't log as quaternion
                if self._data_received_count % 20 == 1:
                    accel = data_dict.get('accel', [0, 0, 0])
                    self.log_status(f"Receiving raw data: AX:{accel[0]:.2f} AY:{accel[1]:.2f} AZ:{accel[2]:.2f}")
                return  # Don't process as quaternion data
            
            # Extract quaternion data
            if 'q0' not in data_dict:
                self.log_status(f"Unexpected data format: {data_dict}")
                return
            q0, q1, q2, q3 = data['q0'], data['q1'], data['q2'], data['q3']
        else:
            self.log_status(f"Unexpected data format: {type(data)}")
            return
        
        # Apply calibration if available (for raw sensor data if present)
        if self.calibration.is_calibrated and 'accel' in data_dict:
            try:
                accel_calibrated = self.calibration.transform_accel(data_dict['accel'])
                data_dict['accel_calibrated'] = accel_calibrated.tolist()
            except Exception as e:
                pass  # Ignore calibration errors
        
        if self.calibration.is_calibrated and 'gyro' in data_dict:
            try:
                gyro_calibrated = self.calibration.transform_gyro(data_dict['gyro'])
                data_dict['gyro_calibrated'] = gyro_calibrated.tolist()
            except Exception as e:
                pass  # Ignore calibration errors
        
        # Log periodically to show data is coming in
        if self._data_received_count % 20 == 1:
            self.log_status(f"Receiving data: Q0:{q0:.3f} Q1:{q1:.3f} Q2:{q2:.3f} Q3:{q3:.3f}")
        
        if self.is_capturing:
            self.current_data.append(data_dict)
            self.update_data_count()
            
            # Log to status (limit frequency)
            if len(self.current_data) % 10 == 0:
                self.log_status(f"Captured: Q0:{q0:.3f} Q1:{q1:.3f} Q2:{q2:.3f} Q3:{q3:.3f}")
    
    def update_data_count(self):
        """Update data count display"""
        self.data_count_label.config(text=f"Data Points: {len(self.current_data)}")
        
    def log_status(self, message):
        """Log message to status display"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.insert("end", f"[{timestamp}] {message}\n")
        self.status_text.see("end")
    
    def on_connection_lost(self, reason):
        """Callback when connection is lost"""
        self.root.after(0, lambda: self._handle_connection_lost(reason))
    
    def _handle_connection_lost(self, reason):
        """Handle connection lost in main thread"""
        self.log_status(f"CONNECTION LOST: {reason}")
        self.connection_label.config(text="Status: Connection Lost", foreground="orange")
        
        if self.is_capturing:
            # Stop capturing
            self.is_capturing = False
            self.capture_btn.config(text="Start Capture", bg="green")
        
        # Show dialog
        result = messagebox.askyesno(
            "Connection Lost",
            f"Connection lost: {reason}\n\nAttempt to reconnect?"
        )
        
        if result:
            self.log_status("Attempting to reconnect...")
            self.disconnect_serial()
            time.sleep(1)
            self.connect_serial()
        else:
            # User chose not to reconnect, clean up connection
            self.disconnect_serial()
    
    def start_monitoring(self):
        """Start connection monitoring thread"""
        if not self.monitoring:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_connection, daemon=True)
            self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop connection monitoring thread"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread = None
    
    def _monitor_connection(self):
        """Monitor connection health"""
        while self.monitoring:
            try:
                capture = self.serial_capture if self.connection_type == "serial" else self.bluetooth_capture
                
                if capture and capture.is_connected():
                    stats = capture.get_stats()
                    
                    # Log stats periodically
                    if stats['total_received'] > 0 and stats['total_received'] % 100 == 0:
                        self.root.after(0, lambda s=stats: self.log_status(
                            f"Stats: {s['total_received']} received, {s['total_parsed']} parsed ({s['parse_rate']:.1f}%)"
                        ))
                    
                    # Check if data has stopped
                    if stats['seconds_since_data'] and stats['seconds_since_data'] > 3.0:
                        self.root.after(0, lambda s=stats: self.log_status(
                            f"WARNING: No data for {s['seconds_since_data']:.1f} seconds"
                        ))
                        self.root.after(0, lambda: self.connection_label.config(
                            text="Status: Connected (No Data)", foreground="orange"
                        ))
                else:
                    # Connection lost
                    if capture:
                        self.monitoring = False
                        break
                        
            except Exception as e:
                print(f"Monitor error: {e}")
            
            time.sleep(1)  # Check every second
        
    def save_data(self):
        """Save current data to file"""
        if not self.current_data:
            messagebox.showwarning("Warning", "No data to save")
            return
            
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir="data"
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    json.dump({
                        'timestamp': datetime.now().isoformat(),
                        'data_points': len(self.current_data),
                        'data': self.current_data
                    }, f, indent=2)
                self.log_status(f"Data saved to {filename}")
                messagebox.showinfo("Success", "Data saved successfully")
            except Exception as e:
                messagebox.showerror("Save Error", str(e))
                
    def load_data(self):
        """Load data from file"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir="data"
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    loaded = json.load(f)
                    self.current_data = loaded['data']
                    self.update_data_count()
                    self.log_status(f"Loaded {len(self.current_data)} data points from {filename}")
                    messagebox.showinfo("Success", f"Loaded {len(self.current_data)} data points")
            except Exception as e:
                messagebox.showerror("Load Error", str(e))
                
    def visualize_3d(self):
        """Open 3D visualization window"""
        if not self.current_data:
            messagebox.showwarning("Warning", "No data to visualize")
            return
            
        try:
            # Use 'ground' coordinate system: X=left/right (target line), Y=up/down, Z=in/out
            visualizer = SwingVisualizer(self.current_data, coordinate_system='ground')
            visualizer.show()
        except Exception as e:
            messagebox.showerror("Visualization Error", str(e))
            self.log_status(f"Visualization error: {e}")
            
    def start_calibration_wizard(self):
        """Open the calibration wizard"""
        if not self.is_connected():
            messagebox.showerror("Error", "Please connect to a device first")
            return
        
        # Get the current capture device
        capture_device = self.serial_capture if self.connection_type == "serial" else self.bluetooth_capture
        
        # Open calibration wizard with callback to update status when complete
        wizard = CalibrationWizard(self.root, capture_device, self.calibration,
                                  on_complete=self.update_calibration_status)
        
        # Note: No need for self.root.after() - callback handles it
    
    def reset_calibration(self):
        """Reset calibration to default"""
        result = messagebox.askyesno("Reset Calibration", 
            "Are you sure you want to reset the calibration?\n" +
            "This will revert to default (uncalibrated) sensor orientation.")
        
        if result:
            self.calibration.reset_calibration()
            self.update_calibration_status()
            self.log_status("Calibration reset to default")
    
    def update_calibration_status(self):
        """Update calibration status label"""
        status = self.calibration.get_calibration_status()
        self.calib_status_label.config(text=f"Status: {status}")
        
        if self.calibration.is_calibrated:
            self.log_status("Sensor calibration active")
    
    def on_closing(self):
        """Handle window closing"""
        if self.serial_capture:
            self.serial_capture.stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = GolfSwingAnalyzer(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
