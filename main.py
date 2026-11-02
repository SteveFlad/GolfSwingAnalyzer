"""
Golf Swing Analyzer - Main Application
Captures data from ICM-20948 sensor and visualizes 3D golf club path
"""

import json
import math
import sys
import threading
import time
from collections import deque
from datetime import datetime

import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk
import numpy as np

from serial.tools import list_ports

from calibration_wizard import CalibrationWizard
from sensor_calibration import SensorCalibration
from serial_capture import SerialCapture

try:
    from ble_capture import BLEAK_AVAILABLE, BLECapture, scan_ble_devices_sync

    BLUETOOTH_AVAILABLE = BLEAK_AVAILABLE
    BLUETOOTH_TYPE = "BLE (Bluetooth Low Energy)" if BLEAK_AVAILABLE else None
except ImportError:
    BLUETOOTH_AVAILABLE = False
    BLECapture = None
    scan_ble_devices_sync = None
    BLUETOOTH_TYPE = None


class VisualizationFilterDialog:
    """Dialog for configuring visualization filters"""
    
    def __init__(self, parent, current_deadband=0.10, smoothing_window=5, 
                 noise_floor=25.0, filter_type='moving_average'):
        self.result = None
        self.top = tk.Toplevel(parent)
        self.top.title("Visualization Filter Settings")
        self.top.geometry("550x650")  # Increased height to show buttons
        self.top.resizable(True, True)  # Allow resizing if needed
        self.top.transient(parent)
        
        # Center the dialog
        self.top.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.top.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.top.winfo_height() // 2)
        self.top.geometry(f"+{x}+{y}")
        
        # Grab focus after positioning
        self.top.grab_set()
        self.top.focus_force()
        
        # Main frame
        main_frame = ttk.Frame(self.top, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Configure Visualization Filters", 
                               font=("TkDefaultFont", 12, "bold"))
        title_label.pack(pady=(0, 15))
        
        # Deadband (read from current settings)
        deadband_frame = ttk.LabelFrame(main_frame, text="Motion Deadband", padding=10)
        deadband_frame.pack(fill="x", pady=5)
        
        ttk.Label(deadband_frame, text="Minimum rotation per sample (deg):").pack(anchor="w")
        self.deadband_var = tk.DoubleVar(value=current_deadband)
        deadband_slider = ttk.Scale(deadband_frame, from_=0.0, to=1.0, 
                                   variable=self.deadband_var, orient="horizontal")
        deadband_slider.pack(fill="x", pady=5)
        self.deadband_label = ttk.Label(deadband_frame, text=f"{current_deadband:.2f}°")
        self.deadband_label.pack()
        deadband_slider.config(command=self._update_deadband_label)
        
        # Smoothing Window
        smooth_frame = ttk.LabelFrame(main_frame, text="Smoothing Filter", padding=10)
        smooth_frame.pack(fill="x", pady=5)
        
        ttk.Label(smooth_frame, text="Smoothing window size (samples):").pack(anchor="w")
        self.smooth_var = tk.IntVar(value=smoothing_window)
        smooth_slider = ttk.Scale(smooth_frame, from_=1, to=20, 
                                 variable=self.smooth_var, orient="horizontal")
        smooth_slider.pack(fill="x", pady=5)
        self.smooth_label = ttk.Label(smooth_frame, text=f"{smoothing_window} samples")
        self.smooth_label.pack()
        smooth_slider.config(command=self._update_smooth_label)
        
        # Filter Type
        filter_frame = ttk.LabelFrame(main_frame, text="Filter Type", padding=10)
        filter_frame.pack(fill="x", pady=5)
        
        self.filter_type_var = tk.StringVar(value=filter_type)
        ttk.Radiobutton(filter_frame, text="Moving Average (Fast)", 
                       variable=self.filter_type_var, value="moving_average").pack(anchor="w")
        ttk.Radiobutton(filter_frame, text="Savitzky-Golay (Better peak preservation)", 
                       variable=self.filter_type_var, value="savgol").pack(anchor="w")
        ttk.Radiobutton(filter_frame, text="None (Raw data)", 
                       variable=self.filter_type_var, value="none").pack(anchor="w")
        
        # Noise Floor
        noise_frame = ttk.LabelFrame(main_frame, text="Noise Floor", padding=10)
        noise_frame.pack(fill="x", pady=5)
        
        ttk.Label(noise_frame, text="Ignore slowest movements (%):").pack(anchor="w")
        self.noise_var = tk.DoubleVar(value=noise_floor)
        noise_slider = ttk.Scale(noise_frame, from_=0, to=50, 
                                variable=self.noise_var, orient="horizontal")
        noise_slider.pack(fill="x", pady=5)
        self.noise_label = ttk.Label(noise_frame, text=f"{noise_floor:.0f}%")
        self.noise_label.pack()
        noise_slider.config(command=self._update_noise_label)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(15, 0), fill="x")
        
        # Add label above buttons
        ttk.Label(button_frame, text="Click a button to proceed:", 
                 font=("TkDefaultFont", 9, "italic")).pack(pady=(0, 10))
        
        # Button container for horizontal layout
        btn_container = ttk.Frame(button_frame)
        btn_container.pack()
        
        # Try regular tk.Button with colors for visibility
        visualize_btn = tk.Button(btn_container, text="Visualize", command=self._on_ok, 
                                  width=15, bg="#4CAF50", fg="white", font=("TkDefaultFont", 10, "bold"))
        visualize_btn.pack(side="left", padx=5)
        
        cancel_btn = tk.Button(btn_container, text="Cancel", command=self._on_cancel, 
                               width=15, bg="#f44336", fg="white", font=("TkDefaultFont", 10, "bold"))
        cancel_btn.pack(side="left", padx=5)
        
        # Force update to ensure buttons are rendered
        self.top.update_idletasks()
        
        # Handle window close button (X)
        self.top.protocol("WM_DELETE_WINDOW", self._on_cancel)
        
        # Bind Enter and Escape keys
        self.top.bind("<Return>", lambda e: self._on_ok())
        self.top.bind("<Escape>", lambda e: self._on_cancel())
        
    def _update_deadband_label(self, *args):
        val = self.deadband_var.get()
        self.deadband_label.config(text=f"{val:.2f}°")
        
    def _update_smooth_label(self, *args):
        val = int(self.smooth_var.get())
        self.smooth_label.config(text=f"{val} samples")
        
    def _update_noise_label(self, *args):
        val = self.noise_var.get()
        self.noise_label.config(text=f"{val:.0f}%")
        
    def _on_ok(self):
        self.result = {
            'deadband_deg': self.deadband_var.get(),
            'smoothing_window': int(self.smooth_var.get()),
            'noise_floor': self.noise_var.get(),
            'filter_type': self.filter_type_var.get()
        }
        self.top.destroy()
        
    def _on_cancel(self):
        self.result = None
        self.top.destroy()


class GolfSwingAnalyzer:
    def __init__(self, root):
        self.root = root
        self.root.title("Golf Swing Analyzer - v2.0 (Impact Detection)")
        self.root.state('zoomed')  # Maximize window
        
        # Version identifier for capture fix
        self.APP_VERSION = "2.0-IMPACT-FILTER-2026-05-18"
        print("="*70)
        print(f"Golf Swing Analyzer {self.APP_VERSION}")
        print("✓ Continuous streaming buffer with impact detection")
        print("✓ Auto-capture pre/post impact data (configurable buffer size)")
        print("✓ Impact threshold detection (default 800°/s, smoothed over 5 samples)")
        print("✓ Noise filtering: requires 5 consecutive high-velocity samples")
        print("="*70)
        
        self.serial_capture = None
        self.bluetooth_capture = None
        self.connection_type = None  # 'serial' or 'bluetooth'
        self.is_capturing = False
        self.current_data = []
        self.current_filename = None  # Track the current data filename
        
        # Circular buffer for continuous streaming
        self.buffer_size = 150  # Configurable pre/post impact points (150 samples = 1.5s at 100Hz, total 3s swing)
        self.stream_buffer = deque(maxlen=self.buffer_size)
        self.impact_detected = False
        self.pre_impact_data = []
        self.post_impact_data = []
        self.post_impact_count = 0
        self.impact_threshold = 800.0  # Degrees per second threshold for impact detection (real swings are 1000-3000°/s)
        self.prev_quat_for_impact = None
        self.capture_state = "STREAMING"  # States: STREAMING, CAPTURING_POST, READY_TO_SAVE
        self.impact_warmup_count = 0  # Count samples before enabling impact detection
        self.IMPACT_WARMUP_SAMPLES = 20  # Require 20 samples (~0.2s) before detecting impact
        self.consecutive_high_velocity = 0  # Count consecutive samples above threshold
        self.CONSECUTIVE_REQUIRED = 5  # Require 5 consecutive high-velocity samples (0.05s)
        self.debug_angular_velocity = False  # Set to True to log angular velocity values (generates lots of output)
        self.angular_velocity_window = deque(maxlen=10)  # Sliding window for velocity smoothing
        self.VELOCITY_SMOOTHING_SAMPLES = 5  # Average over last N samples
        
        self.monitor_thread = None
        self.monitoring = False
        self.bt_devices = []
        self.settings_file = 'app_settings.json'
        self._save_settings_after_id = None
        self.filtered_prev_quat = None
        self.deadband_profiles = {
            "Off": 0.0,
            "Low": 0.05,
            "Balanced": 0.10,
            "Strong": 0.20,
            "Custom": 0.10,
        }
        self.deadband_profile_var = tk.StringVar(value="Balanced")
        self.deadband_var = tk.DoubleVar(value=self.deadband_profiles["Balanced"])
        
        # Default visualization filter settings
        self.viz_filter_config = {
            'deadband_deg': 0.10,
            'smoothing_window': 5,
            'noise_floor': 25.0,
            'filter_type': 'moving_average'
        }
        
        # Initialize sensor calibration
        self.calibration = SensorCalibration('calibration_data.json')
        
        self.setup_ui()
        self.load_settings()
        self.refresh_ports()
        
    def setup_ui(self):
        """Create the user interface"""
        # Create button font for consistent sizing
        self.button_font = tkfont.nametofont("TkDefaultFont").copy()
        self.button_font.configure(size=int(self.button_font.cget("size") * 1.5))
        
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
        
        self.scan_btn = tk.Button(control_frame, text="Scan", command=self.scan_devices, font=self.button_font, padx=12, pady=6)
        self.scan_btn.grid(row=1, column=3, padx=5, pady=5)
        self.connect_btn = tk.Button(control_frame, text="Connect", command=self.toggle_connection, font=self.button_font, padx=12, pady=6)
        self.connect_btn.grid(row=1, column=4, padx=5, pady=5)
        
        # Capture Controls
        ttk.Label(control_frame, text="Buffer Size:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.buffer_size_var = tk.IntVar(value=150)
        buffer_size_spinbox = ttk.Spinbox(
            control_frame,
            from_=50,
            to=500,
            textvariable=self.buffer_size_var,
            width=8,
            command=self.update_buffer_size
        )
        buffer_size_spinbox.grid(row=2, column=1, sticky="w", padx=5, pady=5)
        buffer_size_spinbox.bind('<Return>', lambda e: self.update_buffer_size())
        ttk.Label(control_frame, text="points").grid(row=2, column=2, sticky="w", padx=0, pady=5)
        
        ttk.Label(control_frame, text="Impact Threshold:").grid(row=2, column=3, sticky="w", padx=5, pady=5)
        self.impact_threshold_var = tk.DoubleVar(value=800.0)
        impact_threshold_spinbox = ttk.Spinbox(
            control_frame,
            from_=100.0,
            to=3000.0,
            increment=50.0,
            textvariable=self.impact_threshold_var,
            width=8,
            command=self.update_impact_threshold
        )
        impact_threshold_spinbox.grid(row=2, column=4, sticky="w", padx=5, pady=5)
        impact_threshold_spinbox.bind('<Return>', lambda e: self.update_impact_threshold())
        ttk.Label(control_frame, text="°/s").grid(row=2, column=5, sticky="w", padx=0, pady=5)
        
        # Action buttons
        ttk.Label(control_frame, text="Actions:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.save_btn = tk.Button(
            control_frame,
            text="Save to File",
            command=self.save_captured_data,
            font=self.button_font,
            padx=12,
            pady=6,
            state="disabled",
            bg="#9e9e9e",
            fg="white"
        )
        self.save_btn.grid(row=3, column=1, padx=5, pady=5)

        tk.Button(control_frame, text="Clear Buffer", command=self.clear_buffer, font=self.button_font, padx=12, pady=6).grid(row=3, column=2, padx=5, pady=5)

        # Live noise filter controls
        ttk.Label(control_frame, text="Noise Filter:").grid(row=4, column=0, sticky="w", padx=5, pady=5)
        self.deadband_profile_combo = ttk.Combobox(
            control_frame,
            textvariable=self.deadband_profile_var,
            values=list(self.deadband_profiles.keys()),
            width=12,
            state="readonly",
        )
        self.deadband_profile_combo.grid(row=4, column=1, sticky="w", padx=5, pady=5)
        self.deadband_profile_combo.bind("<<ComboboxSelected>>", self.on_deadband_profile_changed)

        self.deadband_slider = ttk.Scale(
            control_frame,
            from_=0.0,
            to=0.5,
            variable=self.deadband_var,
            orient="horizontal",
            command=self.on_deadband_slider_changed,
        )
        self.deadband_slider.grid(row=4, column=2, columnspan=2, sticky="ew", padx=5, pady=5)

        self.deadband_value_label = ttk.Label(control_frame, text="0.10 deg/sample")
        self.deadband_value_label.grid(row=4, column=4, sticky="w", padx=5, pady=5)

        tk.Button(control_frame, text="Reset Settings", command=self.reset_settings, font=self.button_font, padx=12, pady=6).grid(
            row=4, column=5, sticky="w", padx=5, pady=5
        )
        
        # File Controls
        file_frame = ttk.LabelFrame(self.root, text="File Management", padding=10)
        file_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Button(file_frame, text="Save Data", command=self.save_data, font=self.button_font, padx=12, pady=6).pack(side="left", padx=5)
        tk.Button(file_frame, text="Load Data", command=self.load_data, font=self.button_font, padx=12, pady=6).pack(side="left", padx=5)
        tk.Button(file_frame, text="Visualize 3D", command=self.visualize_3d, font=self.button_font, padx=12, pady=6).pack(side="left", padx=5)
        
        # Calibration Controls
        calib_frame = ttk.LabelFrame(self.root, text="Sensor Calibration", padding=10)
        calib_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Button(calib_frame, text="Calibrate Sensor", command=self.start_calibration_wizard, font=self.button_font, padx=12, pady=6).pack(side="left", padx=5)
        tk.Button(calib_frame, text="Set Address Reference", command=self.capture_address_reference_only, font=self.button_font, padx=12, pady=6).pack(side="left", padx=5)
        tk.Button(calib_frame, text="Reset Calibration", command=self.reset_calibration, font=self.button_font, padx=12, pady=6).pack(side="left", padx=5)
        
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
        
        # Log version info to confirm fix is loaded
        self.root.after(50, lambda: self.log_status(
            f"✓ Running {self.APP_VERSION} - Capture bug fixed!"))
        
        # Data Summary
        summary_frame = ttk.LabelFrame(self.root, text="Data Summary", padding=10)
        summary_frame.pack(fill="x", padx=10, pady=5)
        
        self.data_count_label = ttk.Label(summary_frame, text="Buffer: 0/150 | State: STREAMING")
        self.data_count_label.pack(side="left", padx=10)
        
        self.connection_label = ttk.Label(summary_frame, text="Status: Not Connected", foreground="red")
        self.connection_label.pack(side="left", padx=10)

        self.update_deadband_label()

    @staticmethod
    def _normalize_quat_wxyz(quat):
        q0, q1, q2, q3 = quat
        norm = math.sqrt(q0 * q0 + q1 * q1 + q2 * q2 + q3 * q3)
        if norm < 1e-12:
            return (1.0, 0.0, 0.0, 0.0)
        return (q0 / norm, q1 / norm, q2 / norm, q3 / norm)

    @staticmethod
    def _quat_conjugate_wxyz(quat):
        q0, q1, q2, q3 = quat
        return (q0, -q1, -q2, -q3)

    @staticmethod
    def _quat_multiply_wxyz(a, b):
        aw, ax, ay, az = a
        bw, bx, by, bz = b
        return (
            aw * bw - ax * bx - ay * by - az * bz,
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
        )

    def _quat_delta_angle_deg(self, prev_quat, curr_quat):
        q_prev = self._normalize_quat_wxyz(prev_quat)
        q_curr = self._normalize_quat_wxyz(curr_quat)
        q_diff = self._quat_multiply_wxyz(q_curr, self._quat_conjugate_wxyz(q_prev))
        q_diff = self._normalize_quat_wxyz(q_diff)
        w = max(-1.0, min(1.0, q_diff[0]))
        return math.degrees(2.0 * math.acos(abs(w)))

    def apply_deadband_filter(self, data_dict):
        current_quat = self._normalize_quat_wxyz((
            float(data_dict['q0']),
            float(data_dict['q1']),
            float(data_dict['q2']),
            float(data_dict['q3']),
        ))

        if self.filtered_prev_quat is None:
            self.filtered_prev_quat = current_quat
            data_dict['q0'], data_dict['q1'], data_dict['q2'], data_dict['q3'] = current_quat
            return

        deadband_deg = float(self.deadband_var.get())
        delta_deg = self._quat_delta_angle_deg(self.filtered_prev_quat, current_quat)

        if delta_deg < deadband_deg:
            data_dict['q0'], data_dict['q1'], data_dict['q2'], data_dict['q3'] = self.filtered_prev_quat
        else:
            self.filtered_prev_quat = current_quat
            data_dict['q0'], data_dict['q1'], data_dict['q2'], data_dict['q3'] = current_quat

    def update_deadband_label(self):
        self.deadband_value_label.config(text=f"{self.deadband_var.get():.2f} deg/sample")

    def on_deadband_profile_changed(self, _event=None):
        profile = self.deadband_profile_var.get()
        if profile in self.deadband_profiles:
            self.deadband_var.set(self.deadband_profiles[profile])
            self.update_deadband_label()
            self.log_status(f"Noise filter profile set to {profile} ({self.deadband_var.get():.2f} deg/sample)")
            self.schedule_save_settings()

    def on_deadband_slider_changed(self, _value=None):
        slider_value = round(float(self.deadband_var.get()), 2)
        self.deadband_var.set(slider_value)
        self.update_deadband_label()
        current_profile = self.deadband_profile_var.get()
        if current_profile != "Custom":
            target = self.deadband_profiles.get(current_profile)
            if target is None or abs(target - slider_value) > 1e-6:
                self.deadband_profile_var.set("Custom")
                self.deadband_profiles["Custom"] = slider_value
        self.schedule_save_settings()

    def reset_settings(self):
        """Restore default noise filter settings and save immediately."""
        default_profile = "Balanced"
        default_value = 0.10
        self.deadband_profiles[default_profile] = default_value
        self.deadband_profiles["Custom"] = default_value
        self.deadband_profile_var.set(default_profile)
        self.deadband_var.set(default_value)
        self.update_deadband_label()
        self.filtered_prev_quat = None

        if self._save_settings_after_id is not None:
            self.root.after_cancel(self._save_settings_after_id)
            self._save_settings_after_id = None

        try:
            self.save_settings()
            self.log_status("Settings reset to defaults (Balanced, 0.10 deg/sample)")
        except Exception as e:
            self.log_status(f"Settings reset warning: {e}")

    def load_settings(self):
        """Load persisted UI settings from disk."""
        try:
            with open(self.settings_file, 'r') as f:
                settings = json.load(f)

            profile = settings.get('deadband_profile', 'Balanced')
            deadband_deg = float(settings.get('deadband_deg', self.deadband_profiles['Balanced']))
            deadband_deg = min(0.5, max(0.0, deadband_deg))

            if profile not in self.deadband_profiles:
                profile = 'Custom'

            self.deadband_var.set(deadband_deg)

            # Keep presets in sync if a known profile has changed value from file.
            if profile != 'Custom':
                self.deadband_profiles[profile] = deadband_deg
            else:
                self.deadband_profiles['Custom'] = deadband_deg

            self.deadband_profile_var.set(profile)
            self.update_deadband_label()
            self.log_status(f"Loaded settings: {profile} ({deadband_deg:.2f} deg/sample)")
        except FileNotFoundError:
            return
        except Exception as e:
            self.log_status(f"Settings load warning: {e}")

    def save_settings(self):
        """Persist UI settings to disk."""
        settings = {
            'deadband_profile': self.deadband_profile_var.get(),
            'deadband_deg': round(float(self.deadband_var.get()), 2),
        }
        with open(self.settings_file, 'w') as f:
            json.dump(settings, f, indent=2)

    def schedule_save_settings(self):
        """Debounce settings writes while the slider is being dragged."""
        if self._save_settings_after_id is not None:
            self.root.after_cancel(self._save_settings_after_id)
        self._save_settings_after_id = self.root.after(250, self._save_settings_safe)

    def _save_settings_safe(self):
        self._save_settings_after_id = None
        try:
            self.save_settings()
        except Exception as e:
            self.log_status(f"Settings save warning: {e}")
        
    def update_connection_ui(self):
        """Update UI based on selected connection type"""
        conn_type = self.conn_type_var.get()
        if conn_type == "serial":
            self.refresh_ports()
        else:
            self.port_combo['values'] = [
                f"{device.name} ({device.address}) RSSI:{device.rssi}"
                + (" [GSA]" if getattr(device, 'is_target', False) else "")
                for device in self.bt_devices
            ]
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
        ports = list_ports.comports()
        # Deduplicate by device name while preserving enumeration order.
        port_list = list(dict.fromkeys(port.device for port in ports))
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
                self.bt_devices = devices
                device_list = [
                    f"{d.name} ({d.address}) RSSI:{d.rssi}" + (" [GSA]" if getattr(d, 'is_target', False) else "")
                    for d in devices
                ]
                self.root.after(0, lambda: self.port_combo.config(values=device_list))
                if device_list:
                    self.root.after(0, lambda: self.port_combo.current(0))
                self.root.after(0, lambda: self.log_status(f"Found {len(devices)} BLE device(s)"))
                target_count = sum(1 for d in devices if getattr(d, 'is_target', False))
                if target_count:
                    self.root.after(0, lambda: self.log_status(f"Detected {target_count} likely GolfSwingAnalyzer device(s) [GSA] - select one of these first"))
                else:
                    self.root.after(0, lambda: self.log_status("No [GSA] device detected; try power-cycling ESP32 and rescanning"))
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
            self.filtered_prev_quat = None
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
                data_callback=self.on_bluetooth_data_received,
                connection_lost_callback=self.on_connection_lost
            )
            self._ble_streaming_confirmed = False
            self.bluetooth_capture.start()
            self.filtered_prev_quat = None
            self.connection_type = "bluetooth"
            self.connection_label.config(text="Status: Connecting via BLE...", foreground="orange")
            self.connect_btn.config(text="Disconnect")
            self.log_status(f"Connecting to {device_addr} via BLE...")
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
            self.filtered_prev_quat = None
            self.connection_type = None
            self.connection_label.config(text="Status: Not Connected", foreground="red")
            self.connect_btn.config(text="Connect")
            self.log_status("Disconnected from USB/Serial")
            self.clear_buffer()  # Clear buffer on disconnect
    
    def disconnect_bluetooth(self):
        """Disconnect from BLE"""
        self.stop_monitoring()
        if self.bluetooth_capture:
            self.bluetooth_capture.stop()
            self.bluetooth_capture = None
            self._ble_streaming_confirmed = False
            self.filtered_prev_quat = None
            self.connection_type = None
            self.connection_label.config(text="Status: Not Connected", foreground="red")
            self.connect_btn.config(text="Connect")
            self.log_status("Disconnected from BLE")
            self.clear_buffer()  # Clear buffer on disconnect
    
    def update_buffer_size(self):
        """Update the buffer size from UI control"""
        try:
            new_size = self.buffer_size_var.get()
            if new_size < 50:
                new_size = 50
                self.buffer_size_var.set(50)
            elif new_size > 500:
                new_size = 500
                self.buffer_size_var.set(500)
            
            self.buffer_size = new_size
            self.stream_buffer = deque(maxlen=self.buffer_size)
            self.log_status(f"Buffer size updated to {new_size} points")
            self.update_data_count()
        except Exception as e:
            self.log_status(f"Error updating buffer size: {e}")
    
    def update_impact_threshold(self):
        """Update the impact detection threshold from UI control"""
        try:
            new_threshold = self.impact_threshold_var.get()
            if new_threshold < 100.0:
                new_threshold = 100.0
                self.impact_threshold_var.set(100.0)
            elif new_threshold > 3000.0:
                new_threshold = 3000.0
                self.impact_threshold_var.set(3000.0)
            
            self.impact_threshold = new_threshold
            self.log_status(f"Impact threshold updated to {new_threshold}°/s")
        except Exception as e:
            self.log_status(f"Error updating impact threshold: {e}")
    
    def clear_buffer(self):
        """Clear the streaming buffer and reset capture state"""
        self.stream_buffer.clear()
        self.pre_impact_data = []
        self.post_impact_data = []
        self.post_impact_count = 0
        self.impact_detected = False
        self.prev_quat_for_impact = None
        self.impact_warmup_count = 0  # Reset warmup counter
        self.consecutive_high_velocity = 0  # Reset consecutive counter
        self.angular_velocity_window.clear()  # Clear velocity smoothing window
        self.capture_state = "STREAMING"
        self.current_data = []
        self.save_btn.config(state="disabled", bg="#9e9e9e")
        self.update_data_count()
        self.log_status("Buffer cleared, streaming continues")
    
    def save_captured_data(self):
        """Save the captured pre+post impact data to file"""
        if self.capture_state != "READY_TO_SAVE":
            messagebox.showwarning("Warning", "No impact data captured yet")
            return
        
        if not self.pre_impact_data and not self.post_impact_data:
            messagebox.showwarning("Warning", "No data to save")
            return
        
        # Combine pre and post impact data
        combined_data = self.pre_impact_data + self.post_impact_data
        
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
                        'data_points': len(combined_data),
                        'pre_impact_points': len(self.pre_impact_data),
                        'post_impact_points': len(self.post_impact_data),
                        'buffer_size': self.buffer_size,
                        'impact_threshold': self.impact_threshold,
                        'filter_config': self.viz_filter_config,
                        'data': combined_data
                    }, f, indent=2)
                self.log_status(f"Impact data saved: {len(combined_data)} points ({len(self.pre_impact_data)} pre + {len(self.post_impact_data)} post)")
                messagebox.showinfo("Success", f"Saved {len(combined_data)} points\n({len(self.pre_impact_data)} pre-impact + {len(self.post_impact_data)} post-impact)")
                
                # Reset to streaming after save
                self.clear_buffer()
            except Exception as e:
                messagebox.showerror("Save Error", str(e))
                self.log_status(f"Save error: {e}")
    
    def detect_impact(self, current_quat):
        """Detect impact based on angular velocity threshold
        
        Requires consecutive high-velocity samples to filter out noise spikes.
        Uses moving average to smooth velocity readings.
        Returns: True if impact detected, False otherwise
        """
        # Initialize or update warmup counter
        if self.impact_warmup_count < self.IMPACT_WARMUP_SAMPLES:
            self.impact_warmup_count += 1
            self.prev_quat_for_impact = current_quat
            
            # Log when warmup completes
            if self.impact_warmup_count == self.IMPACT_WARMUP_SAMPLES:
                self.log_status(f"✓ Impact detection ACTIVE (warmup complete, threshold: {self.impact_threshold}°/s, {self.CONSECUTIVE_REQUIRED} consecutive samples required, smoothing: {self.VELOCITY_SMOOTHING_SAMPLES} samples)")
                self.update_data_count()
            
            return False  # Skip impact detection during warmup
        
        if self.prev_quat_for_impact is None:
            self.prev_quat_for_impact = current_quat
            return False
        
        # Calculate angular change between quaternions
        q0, q1, q2, q3 = current_quat
        p0, p1, p2, p3 = self.prev_quat_for_impact
        
        # Quaternion dot product
        dot = p0*q0 + p1*q1 + p2*q2 + p3*q3
        dot = np.clip(dot, -1.0, 1.0)
        
        # Angular change in radians
        angle_rad = 2 * np.arccos(abs(dot))
        angle_deg = np.rad2deg(angle_rad)
        
        # Assuming 100 Hz sample rate, angular velocity in deg/s
        raw_angular_velocity = angle_deg * 100.0
        
        # Add to sliding window for smoothing
        self.angular_velocity_window.append(raw_angular_velocity)
        
        # Calculate smoothed velocity (average of last N samples)
        if len(self.angular_velocity_window) >= self.VELOCITY_SMOOTHING_SAMPLES:
            # Use only the most recent N samples for averaging
            recent_velocities = list(self.angular_velocity_window)[-self.VELOCITY_SMOOTHING_SAMPLES:]
            smoothed_velocity = sum(recent_velocities) / len(recent_velocities)
        else:
            # Not enough samples yet, use raw velocity
            smoothed_velocity = raw_angular_velocity
        
        # Debug logging - log every sample when debug is enabled
        if self.debug_angular_velocity:
            self.log_status(f"[DEBUG] Raw: {raw_angular_velocity:.1f}°/s | Smoothed: {smoothed_velocity:.1f}°/s | Consecutive: {self.consecutive_high_velocity}/{self.CONSECUTIVE_REQUIRED}")
        
        # Update previous quaternion
        self.prev_quat_for_impact = current_quat
        
        # Check if SMOOTHED velocity exceeds threshold
        if smoothed_velocity > self.impact_threshold:
            self.consecutive_high_velocity += 1
            
            # Only trigger impact after consecutive high-velocity samples
            if self.consecutive_high_velocity >= self.CONSECUTIVE_REQUIRED:
                self.log_status(f"🎯 IMPACT TRIGGERED! Smoothed velocity: {smoothed_velocity:.1f}°/s (raw: {raw_angular_velocity:.1f}°/s)")
                self.consecutive_high_velocity = 0  # Reset for next detection
                return True
        else:
            # Reset counter if velocity drops below threshold
            self.consecutive_high_velocity = 0
        
        return False
    
    def _set_save_button_enabled(self, enabled):
        """Enable or disable the save button"""
        if enabled:
            self.save_btn.config(state="normal", bg="#2e7d32", fg="white",
                               activebackground="#1b5e20", activeforeground="white")
        else:
            self.save_btn.config(state="disabled", bg="#9e9e9e", fg="white")
            
    def clear_data(self):
        """Legacy method - now calls clear_buffer"""
        self.clear_buffer()

    def on_bluetooth_data_received(self, data):
        """Handle BLE callback on tkinter main thread for safe UI updates"""
        self.root.after(0, lambda d=data: self.on_data_received(d))
        
    def on_data_received(self, data):
        """Callback when new data is received from serial or BLE
        
        New behavior: Continuously streams data into circular buffer,
        detects impact, and captures pre/post impact data.
        """
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
        if self.connection_type == "bluetooth" and not getattr(self, "_ble_streaming_confirmed", False):
            self._ble_streaming_confirmed = True
            self.connection_label.config(text="Status: Connected via BLE (Streaming)", foreground="green")
            self.log_status("BLE stream active")

        if self._data_received_count % 20 == 1:
            transport_tag = "BLE" if self.connection_type == "bluetooth" else "USB"
            self.log_status(
                f"Streaming [{transport_tag}]: Q0:{q0:.3f} Q1:{q1:.3f} Q2:{q2:.3f} Q3:{q3:.3f} | State: {self.capture_state}"
            )
        
        # NEW BUFFER-BASED CAPTURE SYSTEM
        current_quat = (q0, q1, q2, q3)
        
        if self.capture_state == "STREAMING":
            # Continuously add to circular buffer
            self.stream_buffer.append(data_dict.copy())
            
            # Check for impact
            if self.detect_impact(current_quat):
                # Impact detected! Lock the pre-impact buffer
                self.pre_impact_data = list(self.stream_buffer)
                self.post_impact_data = []
                self.post_impact_count = 0
                self.capture_state = "CAPTURING_POST"
                self.log_status(f"🎯 IMPACT DETECTED! Captured {len(self.pre_impact_data)} pre-impact points, collecting post-impact...")
                self.update_data_count()
                
        elif self.capture_state == "CAPTURING_POST":
            # Collecting post-impact data
            self.post_impact_data.append(data_dict.copy())
            self.post_impact_count += 1
            
            if self.post_impact_count >= self.buffer_size:
                # Finished capturing post-impact
                self.capture_state = "READY_TO_SAVE"
                self.log_status(f"✓ Post-impact capture complete! {len(self.post_impact_data)} points. Ready to save.")
                self._set_save_button_enabled(True)
                self.update_data_count()
                
                # Also populate current_data for visualization
                self.current_data = self.pre_impact_data + self.post_impact_data
                
        # Apply live quaternion deadband filtering ONLY for display (not captured data)
        try:
            self.apply_deadband_filter(data_dict)
            q0, q1, q2, q3 = data_dict['q0'], data_dict['q1'], data_dict['q2'], data_dict['q3']
        except Exception:
            pass
    
    def update_data_count(self):
        """Update data count display with buffer status"""
        if self.capture_state == "STREAMING":
            warmup_status = ""
            if self.impact_warmup_count < self.IMPACT_WARMUP_SAMPLES:
                warmup_status = f" [WARMUP {self.impact_warmup_count}/{self.IMPACT_WARMUP_SAMPLES}]"
            status_text = f"Buffer: {len(self.stream_buffer)}/{self.buffer_size} | State: STREAMING{warmup_status}"
        elif self.capture_state == "CAPTURING_POST":
            status_text = f"Pre: {len(self.pre_impact_data)} | Post: {self.post_impact_count}/{self.buffer_size} | State: CAPTURING"
        elif self.capture_state == "READY_TO_SAVE":
            total = len(self.pre_impact_data) + len(self.post_impact_data)
            status_text = f"Captured: {total} points ({len(self.pre_impact_data)}+{len(self.post_impact_data)}) | State: READY"
        else:
            status_text = f"State: {self.capture_state}"
        
        self.data_count_label.config(text=status_text)
        
    def log_status(self, message):
        """Log message to status display"""
        try:
            if self.status_text.winfo_exists():
                timestamp = datetime.now().strftime("%H:%M:%S")
                self.status_text.insert("end", f"[{timestamp}] {message}\n")
                self.status_text.see("end")
        except (tk.TclError, AttributeError):
            # Widget destroyed or doesn't exist - ignore
            pass
    
    def on_connection_lost(self, reason):
        """Callback when connection is lost"""
        self.root.after(0, lambda: self._handle_connection_lost(reason))
    
    def _handle_connection_lost(self, reason):
        """Handle connection lost in main thread"""
        self._ble_streaming_confirmed = False
        self.log_status(f"CONNECTION LOST: {reason}")
        self.connection_label.config(text="Status: Connection Lost", foreground="orange")
        self.clear_buffer()  # Clear buffer on connection lost
        
        # Show dialog
        result = messagebox.askyesno(
            "Connection Lost",
            f"Connection lost: {reason}\n\nAttempt to reconnect?"
        )
        
        if result:
            self.log_status("Attempting to reconnect...")
            # Disconnect based on connection type
            if self.connection_type == "serial":
                self.disconnect_serial()
                time.sleep(1)
                self.connect_serial()
            elif self.connection_type == "bluetooth":
                self.disconnect_bluetooth()
                time.sleep(1)
                self.connect_bluetooth()
        else:
            # User chose not to reconnect, clean up connection based on type
            if self.connection_type == "serial":
                self.disconnect_serial()
            elif self.connection_type == "bluetooth":
                self.disconnect_bluetooth()
    
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
                data_point_count = len(self.current_data)
                with open(filename, 'w') as f:
                    json.dump({
                        'timestamp': datetime.now().isoformat(),
                        'data_points': data_point_count,
                        'filter_config': self.viz_filter_config,
                        'data': self.current_data
                    }, f, indent=2)
                self.current_filename = filename  # Store the filename
                self.log_status(f"Data saved to {filename} with filter configuration")
                messagebox.showinfo("Success", f"{data_point_count} points saved successfully")
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
                    
                    # Load filter configuration if available
                    if 'filter_config' in loaded:
                        self.viz_filter_config = loaded['filter_config']
                        self.log_status(f"Loaded filter config: {self.viz_filter_config['filter_type']}")
                    else:
                        # Use defaults for older files
                        self.viz_filter_config = {
                            'deadband_deg': 0.10,
                            'smoothing_window': 5,
                            'noise_floor': 25.0,
                            'filter_type': 'moving_average'
                        }
                        self.log_status("No filter config in file, using defaults")
                    
                    self.current_filename = filename  # Store the filename
                    self.filtered_prev_quat = None
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
        
        # Use current capture deadband as default for visualization
        # (User's "Noise Filter" setting should carry over)
        current_capture_deadband = self.deadband_var.get()
        
        # Show filter configuration dialog with saved settings
        self.log_status(f"Opening filter settings dialog (using capture deadband: {current_capture_deadband:.2f}°)...")
        dialog = VisualizationFilterDialog(
            self.root, 
            current_deadband=current_capture_deadband,  # Use capture setting, not saved viz setting
            smoothing_window=self.viz_filter_config['smoothing_window'],
            noise_floor=self.viz_filter_config['noise_floor'],
            filter_type=self.viz_filter_config['filter_type']
        )
        self.root.wait_window(dialog.top)
        
        if dialog.result is None:
            self.log_status("Visualization cancelled by user")
            return  # User cancelled
        
        # Store the filter configuration for future use
        self.viz_filter_config = dialog.result
            
        try:
            from visualizer import SwingVisualizer
            # Log the filter settings being applied
            self.log_status(f"Visualizing with filters: {dialog.result['filter_type']}, "
                          f"window={dialog.result['smoothing_window']}, "
                          f"deadband={dialog.result['deadband_deg']:.2f}°, "
                          f"noise_floor={dialog.result['noise_floor']:.0f}%")
            
            # Use 'ground' coordinate system: X=left/right (target line), Y=up/down, Z=in/out
            visualizer = SwingVisualizer(
                self.current_data,
                coordinate_system='ground',
                deadband_deg=dialog.result['deadband_deg'],
                smoothing_window=dialog.result['smoothing_window'],
                noise_floor_percentile=dialog.result['noise_floor'],
                filter_type=dialog.result['filter_type'],
                filename=self.current_filename,
                calibration=self.calibration  # Pass calibration for address reference
            )
            self.log_status("Showing visualization window...")
            
            # Show visualization (this blocks until window is closed)
            visualizer.show()
            
            self.log_status("Visualization window closed")
        except Exception as e:
            import traceback
            error_msg = f"Visualization error: {str(e)}"
            try:
                messagebox.showerror("Visualization Error", str(e))
            except:
                pass
            self.log_status(error_msg)
            print(f"ERROR: {error_msg}")
            print(traceback.format_exc())
            
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
    
    def capture_address_reference_only(self):
        """Capture only the address reference without full calibration"""
        if not self.is_connected():
            messagebox.showerror("Error", "Please connect to a device first")
            return
        
        # Get the current capture device
        capture_device = self.serial_capture if self.connection_type == "serial" else self.bluetooth_capture
        
        # Create a simplified wizard that goes straight to address capture
        wizard = CalibrationWizard(self.root, capture_device, self.calibration,
                                  on_complete=self.update_calibration_status)
        
        # Immediately trigger address capture (skip intro)
        wizard.dialog.after(100, wizard.capture_address_reference)
    
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
        try:
            self.save_settings()
        except Exception:
            pass
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
