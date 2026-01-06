"""
Calibration Wizard Dialog
Guides user through sensor calibration process
"""

import tkinter as tk
from tkinter import ttk, messagebox
import time
import numpy as np


class CalibrationWizard:
    """
    Interactive wizard for calibrating the ICM-20948 sensor orientation
    """
    
    def __init__(self, parent, capture_device, calibration_obj):
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
        """
        self.parent = parent
        self.capture = capture_device
        self.calibration = calibration_obj
        
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
        
        self.start_btn = ttk.Button(button_frame, text="Start Calibration", 
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
   • Click "Start Calibration" to begin

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
        
        self.start_btn.config(text="Collect", state="normal", 
                             command=lambda: self.collect_simple())
    
    def collect_simple(self):
        """Collect samples for simple calibration"""
        self.start_btn.config(state="disabled")
        self.update_instructions("Collecting samples... Hold steady!\n\nSamples: 0/50")
        
        self.position_samples['address'] = []
        self.sample_count = 0
        self.target_samples = 50
        self.collecting = True
        
        # Start collection with callback
        self.collect_samples_simple()
    
    def collect_samples_simple(self):
        """Collect samples with timer for simple calibration"""
        if not self.collecting or self.sample_count >= self.target_samples:
            # Finish collection
            self.collecting = False
            # Disable calibration mode
            if hasattr(self.capture, 'disable_calibration_mode'):
                self.capture.disable_calibration_mode()
            self.finish_simple_calibration()
            return
        
        # Enable calibration mode on first call
        if self.sample_count == 0:
            if hasattr(self.capture, 'enable_calibration_mode'):
                self.capture.enable_calibration_mode()
                # Wait a bit for mode to activate
                self.dialog.after(200, self.collect_samples_simple)
                return
        
        # Try to get current data from capture device
        try:
            # Request fresh data
            if hasattr(self.capture, 'get_latest_raw_data'):
                raw_data = self.capture.get_latest_raw_data()
                if raw_data and 'accel' in raw_data:
                    accel = raw_data['accel']
                    self.position_samples['address'].append(accel)
                    self.sample_count += 1
                    
                    # Update progress
                    self.update_instructions(
                        f"Collecting samples... Hold steady!\n\nSamples: {self.sample_count}/{self.target_samples}")
                    progress = int((self.sample_count / self.target_samples) * 100)
                    self.progress_var.set(progress)
        except Exception as e:
            print(f"Error collecting sample: {e}")
        
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
        self.position_samples[self.current_position] = []
        
        self.update_instructions(f"Collecting {self.current_position} data...\nHold steady!\n\nSamples: 0/{self.target_samples}")
        
        # Start collection loop
        self.collect_samples_loop()
    
    def collect_samples_loop(self):
        """Loop to collect samples for current position"""
        if not self.collecting or self.sample_count >= self.target_samples:
            # Finish this position
            self.collecting = False
            # Disable calibration mode after last position
            if self.current_position == 'face_up':
                if hasattr(self.capture, 'disable_calibration_mode'):
                    self.capture.disable_calibration_mode()
            self.finish_position()
            return
        
        # Enable calibration mode on first call of first position
        if self.sample_count == 0 and self.current_position == 'address':
            if hasattr(self.capture, 'enable_calibration_mode'):
                self.capture.enable_calibration_mode()
                # Wait a bit for mode to activate
                self.dialog.after(200, self.collect_samples_loop)
                return
        
        # Try to get current data
        try:
            if hasattr(self.capture, 'get_latest_raw_data'):
                raw_data = self.capture.get_latest_raw_data()
                if raw_data and 'accel' in raw_data:
                    accel = raw_data['accel']
                    self.position_samples[self.current_position].append(accel)
                    self.sample_count += 1
                    
                    # Update UI
                    self.update_instructions(
                        f"Collecting {self.current_position} data...\nHold steady!\n\n" +
                        f"Samples: {self.sample_count}/{self.target_samples}")
        except Exception as e:
            print(f"Error collecting sample: {e}")
        
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
            messagebox.showinfo("Success", 
                "Full calibration complete!\n\n" +
                "The sensor orientation has been calibrated.\n" +
                "Your sensor data will now be properly oriented to the club frame.")
            self.close()
        else:
            messagebox.showerror("Error", 
                "Calibration failed. Please try again.\n" +
                "Make sure to hold the club steady in each position.")
            self.close()
    
    def close(self):
        """Close the dialog"""
        self.collecting = False
        # Make sure to disable calibration mode
        if hasattr(self.capture, 'disable_calibration_mode'):
            self.capture.disable_calibration_mode()
        self.dialog.destroy()
