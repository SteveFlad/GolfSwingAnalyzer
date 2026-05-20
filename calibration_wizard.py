"""
Calibration Wizard Dialog
Guides user through sensor calibration process
"""

import time
import tkinter as tk
from tkinter import messagebox, ttk

import numpy as np


class CalibrationWizard:
    """
    Interactive wizard for calibrating the ICM-20948 sensor orientation
    """
    
    def __init__(self, parent, capture_device, calibration_obj, on_complete=None):
        """
        Initialize calibration wizard
        
        Parameters:
        -----------
        parent : tk.Tk or tk.Toplevel
            Parent window
        capture_device : SerialCapture or BLECapture
            Device to capture data from
        calibration_obj : SensorCalibration
            Calibration object to update
        on_complete : callable, optional
            Callback function to call when calibration completes successfully
        """
        self.parent = parent
        self.capture = capture_device
        self.calibration = calibration_obj
        self.on_complete = on_complete
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Sensor Calibration Wizard")
        self.dialog.geometry("600x500")
        self.dialog.resizable(False, False)
        
        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Calibration data storage
        self.position_samples = {
            'address': [],
            'toe_up': [],
            'toe_down': [],
            'face_up': []
        }
        
        self.current_position = None
        self.collecting = False
        self.sample_count = 0
        self.target_samples = 50  # Samples per position
        self.attempt_count = 0  # Track total attempts to prevent infinite loops
        self.max_attempts = 500  # Max attempts (500 * 40ms = 20 seconds)
        self.calibration_initialized = False  # Track if calibration mode has been enabled
        
        self.setup_ui()
        
        # Center dialog on parent
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.dialog.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
    
    def setup_ui(self):
        """Create the wizard UI"""
        # Title
        title_frame = ttk.Frame(self.dialog)
        title_frame.pack(fill="x", padx=20, pady=10)
        
        title_label = ttk.Label(title_frame, text="Sensor Calibration Wizard", 
                                font=("Arial", 16, "bold"))
        title_label.pack()
        
        subtitle_label = ttk.Label(title_frame, 
                                    text="Follow the instructions to calibrate your sensor orientation",
                                    font=("Arial", 10))
        subtitle_label.pack()
        
        # Instructions frame
        inst_frame = ttk.LabelFrame(self.dialog, text="Instructions", padding=10)
        inst_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.instruction_text = tk.Text(inst_frame, height=12, wrap="word", 
                                        font=("Arial", 10), state="disabled")
        self.instruction_text.pack(fill="both", expand=True)
        
        # Progress frame
        progress_frame = ttk.Frame(self.dialog)
        progress_frame.pack(fill="x", padx=20, pady=5)
        
        ttk.Label(progress_frame, text="Progress:").pack(side="left")
        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                            maximum=100, length=300)
        self.progress_bar.pack(side="left", padx=10)
        
        self.progress_label = ttk.Label(progress_frame, text="0/4 positions")
        self.progress_label.pack(side="left")
        
        # Button frame
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill="x", padx=20, pady=10)
        
        self.start_btn = ttk.Button(button_frame, text="Full Calibration", 
                                     command=self.start_calibration)
        self.start_btn.pack(side="left", padx=5)
        
        self.skip_btn = ttk.Button(button_frame, text="Simple Calibration", 
                                    command=self.simple_calibration)
        self.skip_btn.pack(side="left", padx=5)
        
        ttk.Button(button_frame, text="Cancel", 
                   command=self.close).pack(side="right", padx=5)
        
        # Show initial instructions
        self.show_intro()
    
    def show_intro(self):
        """Show introduction message"""
        intro = """Welcome to the Sensor Calibration Wizard!

The ICM-20948 sensor can be mounted on your golf club in different orientations. This wizard will help calibrate the sensor axes to match the club's natural orientation.

Two calibration methods are available:

1. FULL CALIBRATION (Recommended):
   • More accurate orientation mapping
   • Requires 4 club positions
   • Takes about 2 minutes
   • Click "Full Calibration" to begin

2. SIMPLE CALIBRATION (Quick):
   • Basic gravity-based alignment
   • Only requires address position
   • Takes 30 seconds
   • Click "Simple Calibration"

Make sure your sensor is securely mounted to the club head before proceeding.
"""
        self.update_instructions(intro)
    
    def update_instructions(self, text):
        """Update instruction text"""
        self.instruction_text.config(state="normal")
        self.instruction_text.delete("1.0", "end")
        self.instruction_text.insert("1.0", text)
        self.instruction_text.config(state="disabled")
    
    def start_calibration(self):
        """Start the full calibration process"""
        # Clear previous data
        for key in self.position_samples:
            self.position_samples[key] = []
        
        self.start_btn.config(state="disabled")
        self.skip_btn.config(state="disabled")
        
        # Start with first position
        self.calibrate_position('address')
    
    def simple_calibration(self):
        """Perform simple gravity-based calibration"""
        print("[WIZARD DEBUG] simple_calibration() called!")
        self.start_btn.config(state="disabled")
        self.skip_btn.config(state="disabled")
        
        instructions = """SIMPLE CALIBRATION - Address Position

Hold the club in the normal address position:
• Club head on ground or hovering just above
• Shaft at normal address angle
• Club face square to target
• Hold steady

Click "Collect" when ready. Keep the club steady for 2 seconds.
"""
        self.update_instructions(instructions)
        
        print("[WIZARD DEBUG] Setting up Collect button...")
        self.start_btn.config(text="Collect", state="normal", 
                             command=self.collect_simple)
        print("[WIZARD DEBUG] Button configured!")
    
    def collect_simple(self):
        """Collect samples for simple calibration"""
        print("[WIZARD DEBUG] collect_simple() called!")
        
        # Prevent restarting if already collecting
        if self.collecting:
            print("[WIZARD DEBUG] Already collecting, ignoring button click")
            return
        
        self.start_btn.config(state="disabled")
        self.update_instructions("Collecting samples... Hold steady!\n\nSamples: 0/50")
        
        self.position_samples['address'] = []
        self.sample_count = 0
        self.attempt_count = 0
        self.target_samples = 50
        self.collecting = True
        self.calibration_initialized = False  # Reset for this collection
        
        print(f"[WIZARD DEBUG] Starting collection loop, collecting={self.collecting}")
        # Start collection with callback
        self.collect_samples_simple()
    
    def collect_samples_simple(self):
        """Collect samples with timer for simple calibration"""
        print(f"[WIZARD DEBUG] collect_samples_simple called, collecting={self.collecting}, count={self.sample_count}")
        
        # Check for timeout
        if self.attempt_count >= self.max_attempts:
            self.collecting = False
            if hasattr(self.capture, 'disable_calibration_mode'):
                self.capture.disable_calibration_mode()
            messagebox.showerror("Timeout", 
                f"Collection timed out after {self.max_attempts * 40 / 1000:.1f} seconds.\n"
                f"Only collected {self.sample_count}/{self.target_samples} samples.\n\n"
                "Make sure the sensor is connected and sending data.")
            self.close()
            return
        
        if not self.collecting or self.sample_count >= self.target_samples:
            # Finish collection
            self.collecting = False
            # Disable calibration mode
            if hasattr(self.capture, 'disable_calibration_mode'):
                self.capture.disable_calibration_mode()
            self.finish_simple_calibration()
            return
        
        self.attempt_count += 1
        
        # Enable calibration mode on first call (only once)
        if not self.calibration_initialized:
            self.calibration_initialized = True
            print("[WIZARD] ==> Enabling calibration mode (first time)...")
            if hasattr(self.capture, 'enable_calibration_mode'):
                result = self.capture.enable_calibration_mode()
                print(f"[WIZARD] ==> enable_calibration_mode() returned: {result}")
                # Check calibration mode state
                if hasattr(self.capture, 'calibration_mode'):
                    print(f"[WIZARD] ==> capture.calibration_mode = {self.capture.calibration_mode}")
                # Wait a bit for mode to activate and data to start flowing
                self.dialog.after(500, self.collect_samples_simple)  # Increased wait time
                return
            else:
                print("[WIZARD ERROR] capture doesn't have enable_calibration_mode!")
        
        # Try to get current data from capture device
        try:
            # Request fresh data
            if hasattr(self.capture, 'get_latest_raw_data'):
                raw_data = self.capture.get_latest_raw_data()
                
                # Debug: Always show first 10 attempts
                if self.attempt_count <= 10:
                    print(f"[WIZARD] Attempt {self.attempt_count}: raw_data type={type(raw_data)}, is_none={raw_data is None}")
                    if raw_data is not None:
                        print(f"[WIZARD] Attempt {self.attempt_count}: keys={list(raw_data.keys()) if isinstance(raw_data, dict) else 'NOT_A_DICT'}")
                
                if raw_data and 'accel' in raw_data:
                    accel = raw_data['accel']
                    self.position_samples['address'].append(accel)
                    self.sample_count += 1
                    
                    if self.sample_count <= 5:
                        print(f"[WIZARD] ✓ Sample #{self.sample_count} collected! Accel: {accel}")
                    
                    # Update progress
                    self.update_instructions(
                        f"Collecting samples... Hold steady!\n\nSamples: {self.sample_count}/{self.target_samples}")
                    progress = int((self.sample_count / self.target_samples) * 100)
                    self.progress_var.set(progress)
                else:
                    if self.attempt_count <= 10:
                        has_accel = 'accel' in raw_data if isinstance(raw_data, dict) else False
                        print(f"[WIZARD] ✗ Attempt {self.attempt_count}: Invalid data - raw_data={raw_data is not None}, has_accel={has_accel}")
            else:
                if self.sample_count == 0:
                    print("[WIZARD ERROR] Capture device doesn't have get_latest_raw_data method")
        except Exception as e:
            print(f"Error collecting sample: {e}")
            import traceback
            traceback.print_exc()
        
        # Check if we have enough samples
        if self.sample_count >= self.target_samples:
            print(f"[CAL DEBUG] Target reached! Collected {self.sample_count} samples")
            self.finish_simple_calibration()
        else:
            # Schedule next collection
            self.dialog.after(40, self.collect_samples_simple)  # ~25Hz
    
    def finish_simple_calibration(self):
        """Complete simple calibration"""
        if len(self.position_samples['address']) < 20:
            messagebox.showerror("Error", 
                "Not enough samples collected. Make sure the device is connected and sending data.")
            self.close()
            return
        
        # Perform calibration
        success = self.calibration.calibrate_simple(self.position_samples['address'])
        
        if success:
            messagebox.showinfo("Success", 
                "Simple calibration complete!\n\n" +
                "The sensor has been calibrated for basic orientation.")
            if self.on_complete:
                self.on_complete()
            self.close()
        else:
            messagebox.showerror("Error", 
                "Calibration failed. Please try again.")
            self.close()
    
    def calibrate_position(self, position):
        """Start calibration for a specific position"""
        self.current_position = position
        self.sample_count = 0
        
        # Position-specific instructions
        instructions = self.get_position_instructions(position)
        self.update_instructions(instructions)
        
        # Update button
        self.start_btn.config(text="Collect Data", state="normal", 
                             command=lambda: self.collect_position_data())
    
    def get_position_instructions(self, position):
        """Get instructions for each position"""
        instructions = {
            'address': """POSITION 1/4: Address Position

Place the club in the normal address position:
• Club head on ground (or hovering just above)
• Shaft at normal address angle (~60-70°)
• Face square to target
• Hold steady

This position calibrates the vertical (down) direction.

Click "Collect Data" when ready. You'll need to hold steady for 2 seconds.
""",
            'toe_up': """POSITION 2/4: Toe Up

Rotate the club so the TOE points straight UP:
• Hold club horizontally
• Toe (top edge) pointing to sky
• Heel (bottom edge) pointing to ground
• Face perpendicular to ground
• Hold steady

This helps identify the toe-heel axis.

Click "Collect Data" when ready. Hold steady for 2 seconds.
""",
            'toe_down': """POSITION 3/4: Toe Down

Rotate the club so the TOE points straight DOWN:
• Hold club horizontally
• Toe (top edge) pointing to ground
• Heel (bottom edge) pointing to sky
• Face perpendicular to ground
• Hold steady

This confirms the toe-heel axis direction.

Click "Collect Data" when ready. Hold steady for 2 seconds.
""",
            'face_up': """POSITION 4/4: Face Up

Lay the club face flat, pointing UP:
• Club on its back
• Face pointing straight up to sky
• Grip and head at same height (horizontal)
• Hold steady

This calibrates the face normal direction.

Click "Collect Data" when ready. Hold steady for 2 seconds.
"""
        }
        return instructions.get(position, "Unknown position")
    
    def collect_position_data(self):
        """Collect data for current position"""
        self.start_btn.config(state="disabled")
        self.collecting = True
        self.sample_count = 0
        self.attempt_count = 0
        self.calibration_initialized = False  # Reset for this position
        self.position_samples[self.current_position] = []
        
        self.update_instructions(f"Collecting {self.current_position} data...\nHold steady!\n\nSamples: 0/{self.target_samples}")
        
        # Start collection loop
        self.collect_samples_loop()
    
    def collect_samples_loop(self):
        """Loop to collect samples for current position"""
        # Check for timeout
        if self.attempt_count >= self.max_attempts:
            self.collecting = False
            if self.current_position == 'face_up' and hasattr(self.capture, 'disable_calibration_mode'):
                self.capture.disable_calibration_mode()
            messagebox.showerror("Timeout", 
                f"Collection timed out for position '{self.current_position}' after {self.max_attempts * 40 / 1000:.1f} seconds.\n"
                f"Only collected {self.sample_count}/{self.target_samples} samples.\n\n"
                "Make sure the sensor is connected and sending data.")
            self.close()
            return
        
        if not self.collecting or self.sample_count >= self.target_samples:
            # Finish this position
            self.collecting = False
            # Disable calibration mode after last position
            if self.current_position == 'face_up':
                if hasattr(self.capture, 'disable_calibration_mode'):
                    self.capture.disable_calibration_mode()
            self.finish_position()
            return
        
        self.attempt_count += 1
        
        # Enable calibration mode on first call of first position (only once)
        if self.current_position == 'address' and not self.calibration_initialized:
            self.calibration_initialized = True
            print(f"[WIZARD] ==> Enabling calibration mode for {self.current_position} (first time)...")
            if hasattr(self.capture, 'enable_calibration_mode'):
                result = self.capture.enable_calibration_mode()
                print(f"[WIZARD] ==> enable_calibration_mode() returned: {result}")
                if hasattr(self.capture, 'calibration_mode'):
                    print(f"[WIZARD] ==> capture.calibration_mode = {self.capture.calibration_mode}")
                # Wait a bit for mode to activate and data to start flowing
                self.dialog.after(500, self.collect_samples_loop)  # Increased wait time
                return
        
        # Try to get current data
        try:
            if hasattr(self.capture, 'get_latest_raw_data'):
                raw_data = self.capture.get_latest_raw_data()
                
                # Debug: Always show first 10 attempts
                if self.attempt_count <= 10:
                    print(f"[WIZARD] Position {self.current_position}, Attempt {self.attempt_count}: raw_data={raw_data is not None}")
                    if raw_data is not None:
                        print(f"[WIZARD] Keys: {list(raw_data.keys()) if isinstance(raw_data, dict) else 'NOT_A_DICT'}")
                
                if raw_data and 'accel' in raw_data:
                    accel = raw_data['accel']
                    self.position_samples[self.current_position].append(accel)
                    self.sample_count += 1
                    
                    if self.sample_count <= 5:
                        print(f"[WIZARD] ✓ Sample #{self.sample_count} for {self.current_position}: {accel}")
                    
                    # Update UI
                    self.update_instructions(
                        f"Collecting {self.current_position} data...\nHold steady!\n\n" +
                        f"Samples: {self.sample_count}/{self.target_samples}")
                else:
                    if self.attempt_count <= 10:
                        print(f"[WIZARD] ✗ No valid data for {self.current_position}")
        except Exception as e:
            print(f"Error collecting sample: {e}")
            import traceback
            traceback.print_exc()
        
        # Continue loop
        self.dialog.after(40, self.collect_samples_loop)
    
    def finish_position(self):
        """Finish collecting data for current position"""
        if len(self.position_samples[self.current_position]) < 20:
            messagebox.showerror("Error", 
                "Not enough samples collected. Make sure the device is connected and sending data.")
            self.close()
            return
        
        # Update progress
        completed = sum(1 for p in ['address', 'toe_up', 'toe_down', 'face_up'] 
                       if len(self.position_samples[p]) > 0)
        self.progress_var.set(int((completed / 4) * 100))
        self.progress_label.config(text=f"{completed}/4 positions")
        
        # Move to next position or finish
        if self.current_position == 'address':
            self.calibrate_position('toe_up')
        elif self.current_position == 'toe_up':
            self.calibrate_position('toe_down')
        elif self.current_position == 'toe_down':
            self.calibrate_position('face_up')
        elif self.current_position == 'face_up':
            self.finish_calibration()
    
    def finish_calibration(self):
        """Complete the full calibration"""
        self.update_instructions("Processing calibration data...")
        self.progress_var.set(100)
        
        # Perform calibration
        success = self.calibration.calibrate_from_positions(self.position_samples)
        
        if success:
            # Calibration successful, now capture address reference
            response = messagebox.askyesno("Calibration Complete", 
                "Sensor orientation calibration complete!\n\n" +
                "Would you like to set the address position reference?\n\n" +
                "This will normalize all swing data so the club position\n" +
                "at address is always 0,0,0 with 0° face angle.\n\n" +
                "Recommended: Yes")
            
            if response:
                self.capture_address_reference()
            else:
                # Skip address capture
                if self.on_complete:
                    self.on_complete()
                self.close()
        else:
            messagebox.showerror("Error", 
                "Calibration failed. Please try again.\n" +
                "Make sure to hold the club steady in each position.")
            self.close()
    
    def capture_address_reference(self):
        """Capture address position for normalization"""
        # Switch to quaternion mode
        if hasattr(self.capture, 'disable_calibration_mode'):
            self.capture.disable_calibration_mode()
        
        # Reset collection state
        self.address_samples = []
        self.sample_count = 0
        self.target_samples = 50
        
        # Update UI
        self.update_instructions("""FINAL STEP: Address Position Reference

Place your club in the normal ADDRESS position:
• Club head behind ball
• Face square to target
• Normal address posture
• Hold steady

This position will become your reference point (0,0,0).
All swing measurements will be relative to this position.

Click "Capture Address" when ready.""")
        
        self.start_btn.config(text="Capture Address", state="normal", 
                             command=self.start_address_capture)
        self.progress_var.set(0)
    
    def start_address_capture(self):
        """Start capturing address position data"""
        self.start_btn.config(state="disabled")
        self.sample_count = 0
        self.address_samples = []
        self.update_instructions("Capturing address position... Hold steady!")
        self.dialog.after(100, self.collect_address_samples)
    
    def collect_address_samples(self):
        """Collect quaternion samples at address position"""
        try:
            # Get current quaternion data
            if hasattr(self.capture, 'get_latest_raw_data'):
                data = self.capture.get_latest_raw_data()
                
                if data and 'q0' in data:
                    self.address_samples.append([data['q0'], data['q1'], data['q2'], data['q3']])
                    self.sample_count += 1
                    
                    # Update progress
                    progress = int((self.sample_count / self.target_samples) * 100)
                    self.progress_var.set(progress)
                    self.update_instructions(
                        f"Capturing address position... Hold steady!\n\n" +
                        f"Samples: {self.sample_count}/{self.target_samples}")
        except Exception as e:
            print(f"Error collecting address sample: {e}")
        
        # Check if done
        if self.sample_count >= self.target_samples:
            self.finish_address_capture()
        else:
            self.dialog.after(40, self.collect_address_samples)
    
    def finish_address_capture(self):
        """Process and save address reference"""
        if len(self.address_samples) < 20:
            messagebox.showerror("Error",
                "Not enough samples collected. Make sure device is connected.")
            self.close()
            return
        
        try:
            # Calculate average quaternion
            import numpy as np
            from scipy.spatial.transform import Rotation as R
            
            # Import visualizer to calculate position and face angle
            import sys
            sys.path.insert(0, '.')
            from visualizer import SwingVisualizer
            
            # Average quaternions (simple mean for now)
            address_quat_avg = np.mean(self.address_samples, axis=0)
            # Normalize
            address_quat_avg = address_quat_avg / np.linalg.norm(address_quat_avg)
            
            # Calculate position using same method as visualizer
            quat_scipy = np.array([address_quat_avg[1], address_quat_avg[2], address_quat_avg[3], address_quat_avg[0]])
            rot = R.from_quat(quat_scipy)
            
            # Shaft vector in sensor frame
            shaft_sensor = np.array([-1.0, 0.0, 0.0])
            shaft_rotated = rot.apply(shaft_sensor)
            
            # Map to golf coordinates
            golf_shaft = np.array([shaft_rotated[1], shaft_rotated[2], -shaft_rotated[0]])
            
            # Position = shaft direction * club length
            club_length_m = 1.168  # 46" driver
            address_position = golf_shaft * club_length_m
            
            # Calculate face angle
            face_normal_sensor = np.array([0.0, 0.0, 1.0])
            face_rotated = rot.apply(face_normal_sensor)
            golf_face_normal = np.array([face_rotated[1], face_rotated[2], -face_rotated[0]])
            
            # Project onto X-Y plane
            face_normal_xy = np.array([golf_face_normal[0], golf_face_normal[1], 0.0])
            face_normal_xy_norm = np.linalg.norm(face_normal_xy)
            
            if face_normal_xy_norm > 1e-6:
                face_normal_xy /= face_normal_xy_norm
                angle_rad = np.arctan2(face_normal_xy[1], face_normal_xy[0])
                angle_deg = np.degrees(angle_rad)
                address_face_angle = 90 - angle_deg
            else:
                address_face_angle = 0.0
            
            # Save to calibration
            success = self.calibration.set_address_reference(
                address_quat_avg, address_position, address_face_angle)
            
            if success:
                messagebox.showinfo("Success",
                    f"Address reference captured!\n\n" +
                    f"Position: X={address_position[0]:.3f}, Y={address_position[1]:.3f}, Z={address_position[2]:.3f} m\n" +
                    f"Face angle: {address_face_angle:.2f}°\n\n" +
                    f"All swing data will now be normalized to this reference.")
                if self.on_complete:
                    self.on_complete()
                self.close()
            else:
                messagebox.showerror("Error", "Failed to save address reference.")
                self.close()
                
        except Exception as e:
            print(f"Error processing address reference: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to process address reference: {e}")
            self.close()
    
    def close(self):
        """Close the dialog"""
        self.collecting = False
        # Make sure to disable calibration mode
        if hasattr(self.capture, 'disable_calibration_mode'):
            self.capture.disable_calibration_mode()
        self.dialog.destroy()
