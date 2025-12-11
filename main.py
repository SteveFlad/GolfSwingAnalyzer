"""
Golf Swing Analyzer - Main Application
Captures data from ICM-20948 sensor and visualizes 3D golf club path
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import serial.tools.list_ports
from serial_capture import SerialCapture
from visualizer import SwingVisualizer
import threading
import json
from datetime import datetime


class GolfSwingAnalyzer:
    def __init__(self, root):
        self.root = root
        self.root.title("Golf Swing Analyzer")
        self.root.geometry("1000x800")
        
        self.serial_capture = None
        self.is_capturing = False
        self.current_data = []
        
        self.setup_ui()
        self.refresh_ports()
        
    def setup_ui(self):
        """Create the user interface"""
        # Control Frame
        control_frame = ttk.LabelFrame(self.root, text="Controls", padding=10)
        control_frame.pack(fill="x", padx=10, pady=5)
        
        # Serial Port Selection
        ttk.Label(control_frame, text="Serial Port:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(control_frame, textvariable=self.port_var, width=20)
        self.port_combo.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(control_frame, text="Refresh", command=self.refresh_ports).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(control_frame, text="Connect", command=self.connect_serial).grid(row=0, column=3, padx=5, pady=5)
        
        # Capture Controls
        ttk.Label(control_frame, text="Capture:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.start_btn = ttk.Button(control_frame, text="Start Capture", command=self.start_capture)
        self.start_btn.grid(row=1, column=1, padx=5, pady=5)
        
        self.stop_btn = ttk.Button(control_frame, text="Stop Capture", command=self.stop_capture, state="disabled")
        self.stop_btn.grid(row=1, column=2, padx=5, pady=5)
        
        ttk.Button(control_frame, text="Clear Data", command=self.clear_data).grid(row=1, column=3, padx=5, pady=5)
        
        # File Controls
        file_frame = ttk.LabelFrame(self.root, text="File Management", padding=10)
        file_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(file_frame, text="Save Data", command=self.save_data).pack(side="left", padx=5)
        ttk.Button(file_frame, text="Load Data", command=self.load_data).pack(side="left", padx=5)
        ttk.Button(file_frame, text="Visualize 3D", command=self.visualize_3d).pack(side="left", padx=5)
        
        # Status Display
        status_frame = ttk.LabelFrame(self.root, text="Status", padding=10)
        status_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.status_text = tk.Text(status_frame, height=10, wrap="word")
        self.status_text.pack(fill="both", expand=True)
        scrollbar = ttk.Scrollbar(self.status_text)
        scrollbar.pack(side="right", fill="y")
        self.status_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.status_text.yview)
        
        # Data Summary
        summary_frame = ttk.LabelFrame(self.root, text="Data Summary", padding=10)
        summary_frame.pack(fill="x", padx=10, pady=5)
        
        self.data_count_label = ttk.Label(summary_frame, text="Data Points: 0")
        self.data_count_label.pack(side="left", padx=10)
        
        self.connection_label = ttk.Label(summary_frame, text="Status: Not Connected", foreground="red")
        self.connection_label.pack(side="left", padx=10)
        
    def refresh_ports(self):
        """Refresh available serial ports"""
        ports = serial.tools.list_ports.comports()
        port_list = [port.device for port in ports]
        self.port_combo['values'] = port_list
        if port_list:
            self.port_combo.current(0)
        self.log_status(f"Found {len(port_list)} serial port(s)")
        
    def connect_serial(self):
        """Connect to selected serial port"""
        port = self.port_var.get()
        if not port:
            messagebox.showerror("Error", "Please select a serial port")
            return
            
        try:
            self.serial_capture = SerialCapture(port, 115200, self.on_data_received)
            self.serial_capture.start()
            self.connection_label.config(text=f"Status: Connected to {port}", foreground="green")
            self.log_status(f"Connected to {port}")
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
            self.log_status(f"Connection failed: {e}")
            
    def start_capture(self):
        """Start capturing data"""
        if not self.serial_capture or not self.serial_capture.is_connected():
            messagebox.showerror("Error", "Please connect to a serial port first")
            return
            
        self.is_capturing = True
        self.current_data = []
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.log_status("Capture started")
        
    def stop_capture(self):
        """Stop capturing data"""
        self.is_capturing = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.log_status(f"Capture stopped. Total data points: {len(self.current_data)}")
        
    def clear_data(self):
        """Clear current data"""
        self.current_data = []
        self.update_data_count()
        self.log_status("Data cleared")
        
    def on_data_received(self, data):
        """Callback when new data is received from serial"""
        if self.is_capturing:
            self.current_data.append(data)
            self.update_data_count()
            
            # Log to status (limit frequency)
            if len(self.current_data) % 10 == 0:
                self.log_status(f"Q0:{data['q0']:.3f} Q1:{data['q1']:.3f} Q2:{data['q2']:.3f} Q3:{data['q3']:.3f}")
    
    def update_data_count(self):
        """Update data count display"""
        self.data_count_label.config(text=f"Data Points: {len(self.current_data)}")
        
    def log_status(self, message):
        """Log message to status display"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.insert("end", f"[{timestamp}] {message}\n")
        self.status_text.see("end")
        
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
            visualizer = SwingVisualizer(self.current_data)
            visualizer.show()
        except Exception as e:
            messagebox.showerror("Visualization Error", str(e))
            self.log_status(f"Visualization error: {e}")
            
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
