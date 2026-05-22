"""
3D Visualization Module for Golf Swing Analysis
Displays club head path, speed, and face direction
"""

import os
import numpy as np

# Prevent VS Code from opening Interactive window for matplotlib plots
os.environ['MPLBACKEND'] = 'TkAgg'

# Force matplotlib to use GUI backend (not inline for notebooks)
import matplotlib
matplotlib.use('TkAgg')  # Use Tk GUI backend for separate window
# Disable interactive mode to prevent VS Code interception
matplotlib.interactive(False)
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from mpl_toolkits.mplot3d import Axes3D


def _normalize_quaternion_wxyz(quat):
    """Return a normalized quaternion in [w, x, y, z] format."""
    q = np.asarray(quat, dtype=float)
    norm = np.linalg.norm(q)
    if norm < 1e-12:
        return np.array([1.0, 0.0, 0.0, 0.0], dtype=float)
    return q / norm


def _quat_conjugate_wxyz(quat):
    """Quaternion conjugate for [w, x, y, z]."""
    w, x, y, z = quat
    return np.array([w, -x, -y, -z], dtype=float)


def _quat_multiply_wxyz(q1, q2):
    """Hamilton product for quaternions in [w, x, y, z] format."""
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return np.array([
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    ], dtype=float)


def _rotate_vector_by_quaternion_wxyz(quat, vec):
    """Rotate a 3D vector by a quaternion in [w, x, y, z] format."""
    q = _normalize_quaternion_wxyz(quat)
    v_quat = np.array([0.0, vec[0], vec[1], vec[2]], dtype=float)
    q_conj = _quat_conjugate_wxyz(q)
    rotated = _quat_multiply_wxyz(_quat_multiply_wxyz(q, v_quat), q_conj)
    return rotated[1:]


def _quat_delta_rotvec_wxyz(prev_quat, curr_quat):
    """Compute rotation vector for delta quaternion: curr * inverse(prev)."""
    q_prev = _normalize_quaternion_wxyz(prev_quat)
    q_curr = _normalize_quaternion_wxyz(curr_quat)
    q_diff = _normalize_quaternion_wxyz(_quat_multiply_wxyz(q_curr, _quat_conjugate_wxyz(q_prev)))

    # Keep shortest-path rotation by forcing non-negative scalar part.
    if q_diff[0] < 0.0:
        q_diff = -q_diff

    v = q_diff[1:]
    v_norm = np.linalg.norm(v)
    if v_norm < 1e-12:
        return np.zeros(3, dtype=float)

    angle = 2.0 * np.arctan2(v_norm, q_diff[0])
    axis = v / v_norm
    return axis * angle


def _rotvec_to_quat_wxyz(rotvec):
    """Convert rotation vector to quaternion [w, x, y, z]."""
    rv = np.asarray(rotvec, dtype=float)
    angle = np.linalg.norm(rv)
    if angle < 1e-12:
        return np.array([1.0, 0.0, 0.0, 0.0], dtype=float)
    axis = rv / angle
    half = angle * 0.5
    s = np.sin(half)
    return np.array([np.cos(half), axis[0] * s, axis[1] * s, axis[2] * s], dtype=float)


class SwingVisualizer:
    def __init__(self, data, coordinate_system='ground', deadband_deg=0.10, 
                 smoothing_window=5, noise_floor_percentile=25, filter_type='moving_average',
                 filename=None, club_length_m=1.168, calibration=None):
        """
        Initialize visualizer with quaternion data
        
        Parameters:
        -----------
        data: list of dictionaries with keys 'q0', 'q1', 'q2', 'q3', 'timestamp'
        coordinate_system: str
            'ground' - X=left/right (target line), Y=up/down, Z=in/out (toward/away from golfer) (default)
            'club' - X=up shaft, Y=toe-heel, Z=face normal
        deadband_deg: float
            Minimum per-sample angular change to treat as motion.
        smoothing_window: int
            Window size for smoothing filter (3-20 samples)
        noise_floor_percentile: float
            Percentile threshold for noise filtering (0-50%)
        filter_type: str
            Type of smoothing filter: 'moving_average', 'savgol', or 'none'
        filename: str or None
            Optional filename to display in window title
        club_length_m: float
            Club length in meters for converting angular to linear velocity (default 1.168m = 46" driver)
        calibration: SensorCalibration or None
            Calibration object with address reference data (if available)
        """
        self.data = data
        self.positions = []
        self.velocities = []
        self.orientations = []
        self.coordinate_system = coordinate_system
        self.deadband_deg = max(0.0, float(deadband_deg))
        self.deadband_rad = np.deg2rad(self.deadband_deg)
        self.smoothing_window = max(1, min(20, int(smoothing_window)))
        self.noise_floor_percentile = max(0.0, min(50.0, float(noise_floor_percentile)))
        self.filter_type = filter_type
        self.filename = filename
        self.club_length_m = club_length_m
        self.calibration = calibration
        # Conversion factor: rad/s * club_length_m = m/s; m/s * 2.23694 = mph
        self.rad_to_mph = club_length_m * 2.23694
        # Conversion factor: meters to feet
        self.m_to_ft = 3.28084
        
        self.process_data()
        
    def process_data(self):
        """Convert quaternion data to positions and velocities"""
        # Simulate position by integrating orientation changes
        # In a real application, you might use double integration of accelerometer data
        
        position = np.array([0.0, 0.0, 0.0])
        prev_quat = None
        prev_time = None
        raw_speeds = []
        
        for i, point in enumerate(self.data):
            # Extract quaternion
            quat = _normalize_quaternion_wxyz(np.array([point['q0'], point['q1'], point['q2'], point['q3']]))
            
            # Get timestamp (if available, otherwise assume 100Hz)
            if 'timestamp' in point and point['timestamp'] is not None:
                current_time = point['timestamp']
            else:
                current_time = i * 0.01  # Assume 100Hz if no timestamp
            
            # Store orientation
            self.orientations.append(quat)
            
            # Calculate movement direction from rotation change
            if prev_quat is not None and prev_time is not None:
                # Rotation difference as a rotation vector (radians)
                rotvec = _quat_delta_rotvec_wxyz(prev_quat, quat)
                angular_displacement = np.linalg.norm(rotvec)
                
                # Calculate time delta
                time_delta = current_time - prev_time
                if time_delta > 0:
                    # Convert to angular velocity (rad/s)
                    speed = angular_displacement / time_delta
                else:
                    speed = 0.0
                
                if speed < self.deadband_rad:
                    speed = 0.0
                raw_speeds.append(speed)
            else:
                raw_speeds.append(0.0)
                
            prev_quat = quat
            prev_time = current_time
        
        # Apply smoothing filter to reduce noise
        if self.filter_type == 'savgol' and len(raw_speeds) >= self.smoothing_window:
            # Savitzky-Golay filter (preserves peaks better)
            from scipy.signal import savgol_filter
            # Ensure window is odd
            window = self.smoothing_window if self.smoothing_window % 2 == 1 else self.smoothing_window + 1
            window = min(window, len(raw_speeds))  # Can't be larger than data
            if window >= 5:  # Need at least 5 points for order 3
                smoothed_speeds = savgol_filter(raw_speeds, window, 3)
            else:
                smoothed_speeds = np.array(raw_speeds)
        elif self.filter_type == 'moving_average' and self.smoothing_window > 1:
            # Moving average filter
            smoothed_speeds = np.convolve(raw_speeds, np.ones(self.smoothing_window)/self.smoothing_window, mode='same')
        else:
            # No smoothing
            smoothed_speeds = np.array(raw_speeds)
        
        # Build full trajectory by integrating rotational movement into linear path
        # Calculate club head positions using quaternion orientations
        # Method: Each quaternion defines club shaft direction; multiply by length to get club head position
        # Assumes grip is stationary at origin (simplified model)
        
        for i, point in enumerate(self.data):
            quat = _normalize_quaternion_wxyz(np.array([point['q0'], point['q1'], point['q2'], point['q3']]))
            speed = smoothed_speeds[i]
            
            # Define club shaft vector in sensor frame (pointing from grip toward club head)
            # Sensor is mounted on club head; assume shaft points along sensor's -X axis
            shaft_sensor = np.array([-1.0, 0.0, 0.0])  # Unit vector along shaft
            
            # Rotate shaft vector by quaternion to get current orientation
            # Convert wxyz to scipy convention (xyzw) for rotation
            quat_scipy = np.array([quat[1], quat[2], quat[3], quat[0]])
            from scipy.spatial.transform import Rotation as R
            rot = R.from_quat(quat_scipy)
            shaft_rotated = rot.apply(shaft_sensor)
            
            # Map sensor coordinates to golf coordinates
            # Sensor X → Golf -Z (height, inverted), Sensor Y → Golf X (target), Sensor Z → Golf Y (in/out)
            golf_shaft = np.array([shaft_rotated[1], shaft_rotated[2], -shaft_rotated[0]])
            
            # Club head position = grip position (origin) + shaft direction * club length
            position = golf_shaft * self.club_length_m
            
            self.velocities.append(speed)
            self.positions.append(position)
            
        self.positions = np.array(self.positions)
        self.velocities = np.array(self.velocities)
        
        # Always detect address position from the swing data
        # The stored address reference is used for face angle normalization only
        self.address_idx = self._detect_address_position(self.velocities)
        self.address_position_raw = self.positions[self.address_idx].copy()
        
        if hasattr(self, 'calibration') and self.calibration and self.calibration.has_address_reference:
            # Use stored address face angle from calibration
            self.address_face_angle_raw = self.calibration.address_face_angle
            
            print(f"\n=== Using Stored Address Reference ===")
            print(f"Address detected at sample #{self.address_idx}")
            print(f"Position: X={self.address_position_raw[0]:.3f}, Y={self.address_position_raw[1]:.3f}, Z={self.address_position_raw[2]:.3f} m")
            print(f"Stored face angle: {self.address_face_angle_raw:.2f}°")
        else:
            print(f"\n=== Address Position Detection (No Calibration Reference) ===")
            print(f"Address detected at sample #{self.address_idx}")
            print(f"Raw address position: X={self.address_position_raw[0]:.3f}, Y={self.address_position_raw[1]:.3f}, Z={self.address_position_raw[2]:.3f} m")
            print("⚠ Warning: Using detected address. Run calibration wizard to set permanent reference.")
            
            # We'll calculate face angle after building face_angles array (below)
            self.address_face_angle_raw = None
        
        # Calculate club face angles relative to target line at each point
        self.face_angles = []
        for i, point in enumerate(self.data):
            quat = _normalize_quaternion_wxyz(np.array([point['q0'], point['q1'], point['q2'], point['q3']]))
            
            # Define club face normal vector in sensor frame (pointing perpendicular to face)
            # Assume face normal points along sensor's Z axis
            face_normal_sensor = np.array([0.0, 0.0, 1.0])
            
            # Rotate face normal by quaternion to get current orientation
            quat_scipy = np.array([quat[1], quat[2], quat[3], quat[0]])
            from scipy.spatial.transform import Rotation as R
            rot = R.from_quat(quat_scipy)
            face_rotated = rot.apply(face_normal_sensor)
            
            # Map sensor coordinates to golf coordinates
            # Sensor X → Golf -Z, Sensor Y → Golf X, Sensor Z → Golf Y
            golf_face_normal = np.array([face_rotated[1], face_rotated[2], -face_rotated[0]])
            
            # Calculate angle relative to target line (X-axis)
            # Target line is along X-axis (positive X = right for right-handed golfer)
            target_line = np.array([1.0, 0.0, 0.0])
            
            # Project face normal onto X-Y plane (ignore height component)
            face_normal_xy = np.array([golf_face_normal[0], golf_face_normal[1], 0.0])
            face_normal_xy_norm = np.linalg.norm(face_normal_xy)
            
            if face_normal_xy_norm > 1e-6:
                face_normal_xy /= face_normal_xy_norm
                
                # Calculate angle using atan2 for proper sign
                # Positive angle = face pointing left of target (closed for right-handed)
                # Negative angle = face pointing right of target (open for right-handed)
                angle_rad = np.arctan2(face_normal_xy[1], face_normal_xy[0])
                angle_deg = np.degrees(angle_rad)
                
                # Adjust so 0° = square to target, positive = closed, negative = open
                # Face normal pointing along target line (X+) means square
                angle_deg = 90 - angle_deg  # Convert from standard angle to golf angle
            else:
                angle_deg = 0.0
            
            self.face_angles.append(angle_deg)
        
        self.face_angles = np.array(self.face_angles)
        
        # Get address face angle (from calibration or detected)
        if self.address_face_angle_raw is None:
            # Calculate from detected address position
            if hasattr(self, 'address_idx'):
                self.address_face_angle_raw = self.face_angles[self.address_idx]
                print(f"Detected address face angle: {self.address_face_angle_raw:.2f}°")
            else:
                self.address_face_angle_raw = 0.0
                print("Warning: No address index, using 0° as default face angle")
        
        print(f"Raw address face angle: {self.address_face_angle_raw:.2f}°")
        
        # Normalize positions: subtract address position so address becomes origin (0,0,0)
        self.positions = self.positions - self.address_position_raw
        
        # Normalize face angles: subtract address face angle so address becomes 0°
        self.face_angles = self.face_angles - self.address_face_angle_raw
        
        print(f"\n=== After Address Normalization ===")
        if hasattr(self, 'address_idx'):
            print(f"Address position now at: X={self.positions[self.address_idx][0]:.3f}, Y={self.positions[self.address_idx][1]:.3f}, Z={self.positions[self.address_idx][2]:.3f} m")
            print(f"Address face angle now at: {self.face_angles[self.address_idx]:.2f}°")
        else:
            print(f"First sample position: X={self.positions[0][0]:.3f}, Y={self.positions[0][1]:.3f}, Z={self.positions[0][2]:.3f} m")
            print(f"First sample face angle: {self.face_angles[0]:.2f}°")
        
        # Apply cubic spline interpolation to increase point density and reduce max jump
        # This creates smoother trajectories with smaller gaps between samples
        if len(self.positions) > 3:
            from scipy.interpolate import CubicSpline
            from scipy.spatial.transform import Rotation as R, Slerp
            
            # Store original length for impact index scaling
            original_length = len(self.positions)
            
            # Interpolation factor: 4x means we'll have 4x as many points
            interp_factor = 4
            
            # Original sample indices
            t_original = np.arange(original_length)
            
            # New interpolated sample indices (4x denser)
            t_interp = np.linspace(0, original_length - 1, original_length * interp_factor)
            
            # Create cubic splines for positions and scalar values
            cs_x = CubicSpline(t_original, self.positions[:, 0])
            cs_y = CubicSpline(t_original, self.positions[:, 1])
            cs_z = CubicSpline(t_original, self.positions[:, 2])
            cs_vel = CubicSpline(t_original, self.velocities)
            cs_face = CubicSpline(t_original, self.face_angles)
            
            # Generate interpolated arrays
            self.positions = np.column_stack([cs_x(t_interp), cs_y(t_interp), cs_z(t_interp)])
            self.velocities = cs_vel(t_interp)
            self.face_angles = cs_face(t_interp)
            
            # Interpolate orientations using quaternion slerp
            # Convert orientations list to numpy array [w,x,y,z] -> [x,y,z,w] for scipy
            orientations_array = np.array(self.orientations)
            orientations_xyzw = orientations_array[:, [1, 2, 3, 0]]  # Reorder to [x,y,z,w]
            
            # Create Rotation object and Slerp interpolator
            rotations = R.from_quat(orientations_xyzw)
            slerp = Slerp(t_original, rotations)
            
            # Interpolate rotations
            interp_rotations = slerp(t_interp)
            
            # Convert back to [w,x,y,z] format and store as list
            interp_quat_xyzw = interp_rotations.as_quat()
            interp_quat_wxyz = interp_quat_xyzw[:, [3, 0, 1, 2]]  # Reorder to [w,x,y,z]
            self.orientations = [q for q in interp_quat_wxyz]
            
            # Store interpolation factor for later impact index scaling
            self.interp_factor = interp_factor
            self.original_length = original_length
            
            print(f"\nInterpolation applied: {original_length} → {len(self.positions)} samples ({interp_factor}x)")
        else:
            self.interp_factor = 1
            self.original_length = len(self.positions)
        
        # Detect impact point (maximum speed with optional deceleration check)
        self.impact_idx = None
        if len(self.velocities) > 10:
            max_speed_idx = np.argmax(self.velocities)
            max_speed_mph = self.velocities[max_speed_idx] * self.rad_to_mph
            
            print(f"Max speed: {max_speed_mph:.1f} mph at sample #{max_speed_idx}")
            
            # Check for deceleration after peak (characteristic of ball contact)
            if max_speed_idx < len(self.velocities) - 10:
                post_impact_speeds = self.velocities[max_speed_idx:max_speed_idx+10] * self.rad_to_mph
                speed_drop = max_speed_mph - np.min(post_impact_speeds)
                
                print(f"Speed drop after peak: {speed_drop:.1f} mph")
                
                # If speed drops by >5 mph within 0.1s, likely ball contact
                # Lowered threshold from 10 to 5 mph for better detection
                if speed_drop > 5:
                    self.impact_idx = max_speed_idx
                    print(f"✓ Impact detected at sample #{max_speed_idx} ({max_speed_mph:.1f} mph, drop: {speed_drop:.1f} mph)")
                else:
                    # Use max speed as impact if speed is reasonable (>30 mph)
                    if max_speed_mph > 30:
                        self.impact_idx = max_speed_idx
                        print(f"✓ Impact assumed at max speed sample #{max_speed_idx} ({max_speed_mph:.1f} mph)")
                    else:
                        print(f"⚠ No clear impact detected (max speed {max_speed_mph:.1f} mph, drop {speed_drop:.1f} mph)")
            else:
                # Max speed at end of swing
                if max_speed_mph > 30:
                    self.impact_idx = max_speed_idx
                    print(f"✓ Impact assumed at max speed sample #{max_speed_idx} ({max_speed_mph:.1f} mph)")
                else:
                    print(f"⚠ Max speed too low for impact detection: {max_speed_mph:.1f} mph")
        
        # Trajectory is already normalized: address at 0,0,0 with face angle at 0°
        # Just verify bounds and optionally scale for better visualization
        if len(self.positions) > 0:
            # Calculate trajectory bounds in meters (already normalized to address)
            x_min, x_max = np.min(self.positions[:, 0]), np.max(self.positions[:, 0])
            y_min, y_max = np.min(self.positions[:, 1]), np.max(self.positions[:, 1])
            z_min, z_max = np.min(self.positions[:, 2]), np.max(self.positions[:, 2])
            
            x_range = x_max - x_min
            y_range = y_max - y_min
            z_range = z_max - z_min
            
            print(f"\n=== Normalized Trajectory Bounds (meters) ===")
            print(f"X (Target Line): {x_min:.3f} to {x_max:.3f} (range: {x_range:.3f})")
            print(f"Y (In/Out):      {y_min:.3f} to {y_max:.3f} (range: {y_range:.3f})")
            print(f"Z (Height):      {z_min:.3f} to {z_max:.3f} (range: {z_range:.3f})")
            print(f"Address verified at: X={self.positions[self.address_idx][0]:.4f}, Y={self.positions[self.address_idx][1]:.4f}, Z={self.positions[self.address_idx][2]:.4f} m")
            
            # Convert to feet for display
            x_min_ft = x_min * self.m_to_ft
            x_max_ft = x_max * self.m_to_ft
            y_min_ft = y_min * self.m_to_ft
            y_max_ft = y_max * self.m_to_ft
            z_min_ft = z_min * self.m_to_ft
            z_max_ft = z_max * self.m_to_ft
            
            if self.impact_idx is not None:
                impact_ft = self.positions[self.impact_idx] * self.m_to_ft
                ball_pos_str = f"X={impact_ft[0]:.2f} ft, Y={impact_ft[1]:.2f} ft, Z={impact_ft[2]:.2f} ft"
            else:
                ball_pos_str = "N/A"
            
            print(f"\n=== Normalized Trajectory Bounds (feet, relative to address) ===")
            print(f"X (Target Line): {x_min_ft:.2f} to {x_max_ft:.2f} ft")
            print(f"Y (In/Out):      {y_min_ft:.2f} to {y_max_ft:.2f} ft")
            print(f"Z (Height):      {z_min_ft:.2f} to {z_max_ft:.2f} ft")
            print(f"Impact position: {ball_pos_str}")
        
        # Print diagnostic information
        print(f"\n=== Swing Data Analysis (Natural Golf Coordinates) ===")
        print(f"Total samples: {len(self.data)}")
        print(f"Position points: {len(self.positions)}")
        print(f"Position calculation: Relative to address (0,0,0)")
        
        # Detailed speed diagnostics
        max_speed_raw = np.max(raw_speeds)
        max_speed_smoothed = np.max(self.velocities)
        print(f"\nSpeed Analysis:")
        print(f"  Raw max speed: {max_speed_raw:.2f} rad/s ({max_speed_raw * self.rad_to_mph:.1f} mph)")
        print(f"  Smoothed max speed: {max_speed_smoothed:.2f} rad/s ({max_speed_smoothed * self.rad_to_mph:.1f} mph)")
        print(f"  Club length: {self.club_length_m:.3f} m ({self.club_length_m * self.m_to_ft:.2f} ft)")
        print(f"  Conversion factor: {self.rad_to_mph:.3f} mph per rad/s")
        
        # Show first few quaternion samples to diagnose orientation
        if len(self.data) > 5:
            print(f"\nFirst few quaternion samples:")
            for i in range(min(5, len(self.data))):
                q = self.data[i]
                print(f"  Sample {i}: q0={q['q0']:.4f} q1={q['q1']:.4f} q2={q['q2']:.4f} q3={q['q3']:.4f}")
        
        print(f"\nPosition range - Target Line (X): {np.min(self.positions[:, 0]):.3f} to {np.max(self.positions[:, 0]):.3f} m ({np.ptp(self.positions[:, 0]) * self.m_to_ft:.2f} ft)")
        print(f"Position range - In/Out (Y):      {np.min(self.positions[:, 1]):.3f} to {np.max(self.positions[:, 1]):.3f} m ({np.ptp(self.positions[:, 1]) * self.m_to_ft:.2f} ft)")
        print(f"Position range - Height (Z):      {np.min(self.positions[:, 2]):.3f} to {np.max(self.positions[:, 2]):.3f} m ({np.ptp(self.positions[:, 2]) * self.m_to_ft:.2f} ft)")
        total_distance = np.sum(np.linalg.norm(np.diff(self.positions, axis=0), axis=1))
        print(f"Total path length: {total_distance:.3f} m ({total_distance * self.m_to_ft:.2f} ft)")
        
        print("="*60)
        
    def _detect_address_position(self, velocities):
        """
        Detect address position (club stationary behind ball before swing starts).
        
        Returns index of address position.
        
        Strategy:
        - Look for low angular velocity period in first 20% of data
        - Average over several samples to find most stable position
        - Address should be early in capture with minimal movement
        """
        # Only search in first 20% of data (address is before swing)
        search_end = min(len(velocities) // 5, len(velocities))
        
        if search_end < 5:
            # Too few samples, use first sample
            return 0
        
        # Convert velocities to mph for threshold
        velocities_mph = velocities * self.rad_to_mph
        
        # Find periods with low velocity (< 5 mph movement)
        low_velocity_threshold = 5.0  # mph
        low_velocity_mask = velocities_mph[:search_end] < low_velocity_threshold
        
        if np.any(low_velocity_mask):
            # Find the longest continuous low-velocity period
            # This is likely the address position (stationary club)
            address_candidates = np.where(low_velocity_mask)[0]
            
            if len(address_candidates) > 0:
                # Average over the low-velocity period for stability
                # Use middle of the low-velocity period
                return address_candidates[len(address_candidates) // 2]
        
        # Fallback: use lowest velocity point in search range
        return np.argmin(velocities_mph[:search_end])
    
    def show(self):
        """Display the 3D visualization"""
        # Create maximized figure with filter info in title
        filter_info = f"Filters: {self.filter_type.replace('_', ' ').title()} | Window: {self.smoothing_window} | Deadband: {self.deadband_deg:.2f}° | Noise Floor: {self.noise_floor_percentile:.0f}%"
        
        # Extract just the filename (not full path) if available
        import os
        if self.filename:
            display_name = os.path.basename(self.filename)
        else:
            display_name = "Captured Data"
        
        # Create figure with custom layout using GridSpec
        from matplotlib.gridspec import GridSpec
        fig = plt.figure(figsize=(18, 12))
        fig.canvas.manager.set_window_title(display_name)
        fig.suptitle(filter_info, fontsize=10, y=0.995)
        
        # Create custom grid: 3D plot takes left 2/3, other plots on right 1/3
        # Leave space at bottom for slider controls and scale
        gs = GridSpec(4, 2, figure=fig, width_ratios=[2, 1], height_ratios=[1, 1, 1, 1],
                     hspace=0.4, wspace=0.3, top=0.96, bottom=0.14, left=0.05, right=0.98)
        
        # 3D trajectory plot - spans all 4 rows on the left
        ax1 = fig.add_subplot(gs[:, 0], projection='3d')
        
        # Speed over time - top right
        ax2 = fig.add_subplot(gs[0, 1])
        
        # Club face angle - second from top right
        ax_face = fig.add_subplot(gs[1, 1])
        
        # Top view - third from top right
        ax3 = fig.add_subplot(gs[2, 1])
        
        # Side view - bottom right
        ax4 = fig.add_subplot(gs[3, 1])
        
        # Store axes for update function
        self.fig = fig
        self.axes = {'3d': ax1, 'speed': ax2, 'face': ax_face, 'top': ax3, 'side': ax4}
        
        # Create slider axes at bottom with proper spacing
        ax_slider_start = fig.add_axes([0.15, 0.09, 0.65, 0.015])
        ax_slider_end = fig.add_axes([0.15, 0.03, 0.65, 0.015])
        
        # Add coordinate system legend above sliders
        ax_coords = fig.add_axes([0.15, 0.115, 0.30, 0.02])
        ax_coords.axis('off')
        coord_text = 'Golf Coordinates: X = Target Line (±left/right) | Y = In/Out (ball/away) | Z = Height (ground/up)'
        ax_coords.text(0, 0.5, coord_text, fontsize=9, fontweight='bold', 
                      ha='left', va='center', color='darkblue',
                      bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))
        
        # Create sliders
        total_samples = len(self.positions)
        self.slider_start = Slider(ax_slider_start, 'Start Sample', 0, total_samples-1, 
                                   valinit=0, valstep=1, color='lightblue')
        self.slider_end = Slider(ax_slider_end, 'End Sample', 0, total_samples-1, 
                                 valinit=total_samples-1, valstep=1, color='lightblue')
        
        # Add scale indicator between sliders
        ax_scale = fig.add_axes([0.15, 0.055, 0.65, 0.015])
        ax_scale.set_xlim(0, total_samples-1)
        ax_scale.set_ylim(0, 1)
        ax_scale.axis('off')
        
        # Draw scale line
        ax_scale.plot([0, total_samples-1], [0.5, 0.5], 'k-', linewidth=2, alpha=0.3)
        
        # Add tick marks every 10 samples
        marker_interval = 10
        for i in range(0, total_samples, marker_interval):
            ax_scale.plot([i, i], [0.3, 0.7], 'k-', linewidth=1, alpha=0.5)
            if i % 50 == 0:  # Label every 50 samples
                ax_scale.text(i, 0.1, str(i), ha='center', va='top', fontsize=7, alpha=0.7)
        
        # Add final marker
        if (total_samples-1) % marker_interval != 0:
            ax_scale.plot([total_samples-1, total_samples-1], [0.3, 0.7], 'k-', linewidth=1, alpha=0.5)
            ax_scale.text(total_samples-1, 0.1, str(total_samples-1), ha='center', va='top', fontsize=7, alpha=0.7)
        
        # Highlight current range
        self.range_highlight = ax_scale.fill_between([0, total_samples-1], 0.3, 0.7, 
                                                      color='lightblue', alpha=0.5, zorder=3)
        self.ax_scale = ax_scale
        
        # Update function for sliders
        def update(val):
            start = int(self.slider_start.val)
            end = int(self.slider_end.val)
            
            # Ensure start < end
            if start >= end:
                return
            
            # Clear all axes
            for ax_key, ax in self.axes.items():
                ax.clear()
                if ax_key == '3d':
                    # Re-setup 3D axis after clear
                    ax.remove()
                    self.axes['3d'] = fig.add_subplot(gs[:, 0], projection='3d')
            
            # Redraw with filtered range
            self.plot_trajectory(self.axes['3d'], start, end)
            self.plot_speed(self.axes['speed'], start, end)
            self.plot_face_angle(self.axes['face'], start, end)
            self.plot_top_view(self.axes['top'], start, end)
            self.plot_side_view(self.axes['side'], start, end)
            
            # Update range highlight on scale
            self.range_highlight.remove()
            self.range_highlight = self.ax_scale.fill_between([start, end], 0.3, 0.7, 
                                                               color='lightgreen', alpha=0.6, zorder=3)
            
            fig.canvas.draw_idle()
        
        self.slider_start.on_changed(update)
        self.slider_end.on_changed(update)
        
        # Add control buttons
        # Reset button (aligned with end slider)
        ax_btn_reset = fig.add_axes([0.87, 0.03, 0.08, 0.04])
        btn_reset = Button(ax_btn_reset, 'Reset', color='lightgray', hovercolor='gray')
        
        def reset(event):
            self.slider_start.set_val(0)
            self.slider_end.set_val(total_samples-1)
        
        btn_reset.on_clicked(reset)
        
        # Focus Impact button (if impact detected, aligned with start slider)
        if self.impact_idx is not None:
            ax_btn_impact = fig.add_axes([0.87, 0.09, 0.08, 0.04])
            btn_impact = Button(ax_btn_impact, 'Impact', color='gold', hovercolor='orange')
            
            def focus_impact(event):
                # Show ±50 samples around impact
                impact_start = max(0, self.impact_idx - 50)
                impact_end = min(total_samples-1, self.impact_idx + 50)
                self.slider_start.set_val(impact_start)
                self.slider_end.set_val(impact_end)
            
            btn_impact.on_clicked(focus_impact)
        
        # Add 3D View Preset Buttons (positioned in the right column)
        btn_width = 0.10
        btn_height = 0.028
        btn_x = 0.605  # Left edge of right column
        btn_y_start = 0.26  # Positioned between Face Angle and Top View graphs
        btn_spacing = 0.038
        
        # Add label for view buttons
        ax_view_label = fig.add_axes([btn_x, btn_y_start + 0.04, btn_width, 0.02])
        ax_view_label.axis('off')
        ax_view_label.text(0.5, 0.5, '3D View Angles:', ha='center', va='center', 
                          fontsize=9, fontweight='bold')
        
        # Side View button (top position)
        ax_btn_face = fig.add_axes([btn_x, btn_y_start, btn_width, btn_height])
        btn_face = Button(ax_btn_face, 'Side View', color='lightgreen', hovercolor='lightcoral')
        
        def view_face(event):
            # View from behind golfer looking toward ball with floor plane visible
            # elev=0 horizontal view at eye level
            # azim=0 looks down the Y-axis (in/out), target line (X) at bottom
            self.axes['3d'].view_init(elev=0, azim=0, roll=0)
            fig.canvas.draw_idle()
        
        btn_face.on_clicked(view_face)
        
        # Down-the-line button (second position)
        ax_btn_dtl = fig.add_axes([btn_x, btn_y_start - btn_spacing, btn_width, btn_height])
        btn_dtl = Button(ax_btn_dtl, 'Down-Line', color='lightblue', hovercolor='skyblue')
        
        def view_dtl(event):
            # Opposite direction from Side View
            self.axes['3d'].view_init(elev=0, azim=180, roll=0)
            fig.canvas.draw_idle()
        
        btn_dtl.on_clicked(view_dtl)
        
        # Top-down button
        ax_btn_top = fig.add_axes([btn_x, btn_y_start - 2*btn_spacing, btn_width, btn_height])
        btn_top = Button(ax_btn_top, 'Top-Down', color='lightyellow', hovercolor='gold')
        
        def view_top(event):
            self.axes['3d'].view_init(elev=90, azim=0, roll=0)
            fig.canvas.draw_idle()
        
        btn_top.on_clicked(view_top)
        
        # Normal Stance button (fourth position)
        ax_btn_side = fig.add_axes([btn_x, btn_y_start - 3*btn_spacing, btn_width, btn_height])
        btn_side = Button(ax_btn_side, 'Normal Stance', color='lightcoral', hovercolor='salmon')
        
        def view_side(event):
            # Face-on view from the side, looking perpendicular to target line
            self.axes['3d'].view_init(elev=0, azim=90, roll=0)
            fig.canvas.draw_idle()
        
        btn_side.on_clicked(view_side)
        
        # Plot all views with full range initially
        self.plot_trajectory(ax1, 0, total_samples-1)
        self.plot_speed(ax2, 0, total_samples-1)
        self.plot_face_angle(ax_face, 0, total_samples-1)
        self.plot_top_view(ax3, 0, total_samples-1)
        self.plot_side_view(ax4, 0, total_samples-1)
        
        plt.tight_layout()
        
        # Maximize and bring window to front (with robust error handling)
        try:
            # Try different methods to maximize window depending on backend
            manager = fig.canvas.manager
            if hasattr(manager, 'window'):
                # TkAgg backend
                manager.window.state('zoomed')
            elif hasattr(manager, 'frame'):
                # Qt backends
                manager.frame.showMaximized()
            elif hasattr(manager, 'full_screen_toggle'):
                # Some other backends
                manager.full_screen_toggle()
        except Exception as e:
            # If window maximization fails, just continue with default size
            print(f"Note: Could not maximize window ({e}). Continuing with default size.")
        
        # Draw the window first to ensure it exists
        fig.canvas.draw()
        fig.canvas.flush_events()
        
        # Force window to front (above main application window)
        try:
            manager = fig.canvas.manager
            if hasattr(manager, 'window'):
                # Tkinter backend - aggressive window raising
                window = manager.window
                window.lift()
                window.wm_attributes('-topmost', 1)  # Force to top
                window.after(100, lambda: window.wm_attributes('-topmost', 0))  # Remove topmost after brief delay
                window.focus_force()
            elif hasattr(manager, 'frame'):
                # Qt backends
                manager.frame.raise_()
                manager.frame.activateWindow()
        except Exception as e:
            print(f"Note: Could not bring window to front ({e}).")
        
        plt.show()
        
    def plot_trajectory(self, ax, start_idx=None, end_idx=None):
        """Plot 3D trajectory with color-coded speed
        
        Args:
            ax: 3D axis to plot on
            start_idx: Starting sample index (default: 0)
            end_idx: Ending sample index (default: len-1)
        """
        if start_idx is None:
            start_idx = 0
        if end_idx is None:
            end_idx = len(self.positions) - 1
        
        # Filter data to selected range
        positions = self.positions[start_idx:end_idx+1]
        velocities = self.velocities[start_idx:end_idx+1]
        
        # Normalize velocities for colormap
        norm_vel = velocities / (np.max(velocities) + 1e-6)
        
        # Convert positions to feet for display
        positions_ft = positions * self.m_to_ft
        
        # Plot trajectory in natural golf coordinates (X=target, Y=in/out, Z=height)
        scatter = ax.scatter(
            positions_ft[:, 0],  # X: target line
            positions_ft[:, 1],  # Y: in/out
            positions_ft[:, 2],  # Z: height
            c=velocities,  # Use filtered velocities for coloring
            cmap='RdYlGn_r',
            s=20,
            alpha=0.8
        )
        
        # Add THICK continuous line connecting ALL points
        ax.plot(
            positions_ft[:, 0],  # X: target line
            positions_ft[:, 1],  # Y: in/out
            positions_ft[:, 2],  # Z: height
            'b-',
            alpha=0.8,
            linewidth=3
        )
        
        # Add point numbers every 50 samples to show progression  
        step = max(1, len(positions_ft) // 20)
        for i in range(0, len(positions_ft), step):
            actual_sample = start_idx + i
            ax.text(positions_ft[i, 0], positions_ft[i, 1], positions_ft[i, 2], 
                   str(actual_sample), fontsize=8, color='black')
        
        # Mark start and end of visible range
        start_pos_ft = positions_ft[0]
        end_pos_ft = positions_ft[-1]
        ax.scatter(*start_pos_ft, color='green', s=100, marker='o', 
                  label=f'Start (#{start_idx})', zorder=10)
        ax.scatter(*end_pos_ft, color='red', s=100, marker='X', 
                  label=f'End (#{end_idx})', zorder=10)
        
        # Mark impact point and ball if detected and within visible range
        impact_data = None  # Store impact data for diagnostic box
        if self.impact_idx is not None and start_idx <= self.impact_idx <= end_idx:
            relative_impact_idx = self.impact_idx - start_idx
            impact_pos = positions_ft[relative_impact_idx]
            impact_speed = velocities[relative_impact_idx] * self.rad_to_mph
            impact_face_angle = self.face_angles[self.impact_idx]
            
            # Store impact data for diagnostic box
            impact_data = {
                'pos': impact_pos,
                'speed': impact_speed,
                'angle': impact_face_angle
            }
            
            # Ball marker at impact position
            ax.scatter(impact_pos[0], impact_pos[1], impact_pos[2], 
                      color='white', s=150, marker='o', 
                      edgecolors='black', linewidths=3, label='Ball', zorder=12)
            
            # Impact marker (star) at same position
            ax.scatter(impact_pos[0], impact_pos[1], impact_pos[2], 
                      color='gold', s=400, marker='*', 
                      edgecolors='orange', linewidths=2,
                      label=f'Impact (#{self.impact_idx})', zorder=15)
        
        # Calculate trajectory bounds for arrow scaling (in feet)
        x_range = np.ptp(positions_ft[:, 0]) if len(positions_ft) > 1 else 1.0
        y_range = np.ptp(positions_ft[:, 1]) if len(positions_ft) > 1 else 1.0
        z_range = np.ptp(positions_ft[:, 2]) if len(positions_ft) > 1 else 1.0
        avg_range = (x_range + y_range + z_range) / 3.0
        arrow_scale = max(0.02, avg_range * 0.2)  # Scale arrows to 20% of average range
        
        # Add velocity direction arrows at key points
        step = max(1, len(positions_ft) // 10)  # Max 10 arrows
        for i in range(step, len(positions_ft) - step, step):  # Skip first/last to calculate velocity
            # Calculate velocity direction from neighboring positions
            velocity_vec = positions_ft[i + step] - positions_ft[i - step]
            vel_magnitude = np.linalg.norm(velocity_vec)
            
            if vel_magnitude > 1e-6:  # Only show if there's actual movement
                # Normalize and scale velocity vector for arrow
                velocity_direction = (velocity_vec / vel_magnitude) * arrow_scale
                pos = positions_ft[i]
                
                ax.quiver(
                    pos[0], pos[1], pos[2],  # X, Y, Z
                    velocity_direction[0], velocity_direction[1], velocity_direction[2],  # dX, dY, dZ
                    color='darkred', alpha=0.6, arrow_length_ratio=0.8, linewidth=2.5
                )
        
        # Set dynamic axis limits based on actual data range with padding
        x_min_ft, x_max_ft = np.min(positions_ft[:, 0]), np.max(positions_ft[:, 0])
        y_min_ft, y_max_ft = np.min(positions_ft[:, 1]), np.max(positions_ft[:, 1])
        z_min_ft, z_max_ft = np.min(positions_ft[:, 2]), np.max(positions_ft[:, 2])
        
        # Add 20% padding to each axis
        x_padding = max(0.5, (x_max_ft - x_min_ft) * 0.2)  # At least 0.5 ft padding
        y_padding = max(0.5, (y_max_ft - y_min_ft) * 0.2)
        z_padding = max(0.5, (z_max_ft - z_min_ft) * 0.2)
        
        # Ensure Z axis starts at ground (0) if club goes below 1 ft
        z_min_display = 0 if z_min_ft < 1.0 else z_min_ft - z_padding
        
        ax.set_xlim(x_min_ft - x_padding, x_max_ft + x_padding)
        ax.set_ylim(y_min_ft - y_padding, y_max_ft + y_padding)
        ax.set_zlim(z_min_display, z_max_ft + z_padding)
        
        # Draw ground plane (X-Y plane at Z=0) and grid boundaries
        if self.coordinate_system == 'ground':
            from matplotlib.patches import Rectangle
            from mpl_toolkits.mplot3d import art3d
            
            # Get dynamic axis limits
            x_min, x_max = ax.get_xlim()
            y_min, y_max = ax.get_ylim()
            
            # Create ground plane boundary at Z=0
            ground_x = [x_min, x_max, x_max, x_min, x_min]
            ground_y = [y_min, y_min, y_max, y_max, y_min]
            ground_z = [0, 0, 0, 0, 0]
            ax.plot(ground_x, ground_y, ground_z, 'k-', alpha=0.3, linewidth=1)
            
            # Add grid on ground plane (every 1 foot)
            x_min_int, x_max_int = int(np.floor(x_min)), int(np.ceil(x_max))
            y_min_int, y_max_int = int(np.floor(y_min)), int(np.ceil(y_max))
            
            for x_grid in range(x_min_int, x_max_int + 1):
                ax.plot([x_grid, x_grid], [y_min, y_max], [0, 0], 'k-', alpha=0.1, linewidth=0.5)
            for y_grid in range(y_min_int, y_max_int + 1):
                ax.plot([x_min, x_max], [y_grid, y_grid], [0, 0], 'k-', alpha=0.1, linewidth=0.5)
        
        # Set labels for natural golf coordinate system
        if self.coordinate_system == 'ground':
            ax.set_xlabel('TARGET LINE (X-axis, feet)\n← Left of Target | Right of Target →', 
                         fontsize=11, fontweight='bold', labelpad=10)
            ax.set_ylabel('IN/OUT (Y-axis, feet)\n← Ball/Target | Away from Ball →', 
                         fontsize=11, fontweight='bold', labelpad=10)
            ax.set_zlabel('HEIGHT (Z-axis, feet)\n← Ground | Up →', 
                         fontsize=11, fontweight='bold', labelpad=10)
            ax.set_title('3D Club Head Trajectory\n(Golf Coordinates: Target Line, In/Out, Height)', 
                        fontsize=12, fontweight='bold', pad=15)
        else:
            ax.set_xlabel('Shaft (ft)')
            ax.set_ylabel('Face Normal (ft)')
            ax.set_zlabel('Toe/Heel (ft)')
            ax.set_title('3D Club Head Trajectory\n(Red arrows = velocity direction)')
        
        # Set viewing angle: Normal Stance (face-on view from side)
        # elev=0 horizontal view, azim=90 looking perpendicular to target line
        ax.view_init(elev=0, azim=90, roll=0)
        
        # Add diagnostic text overlay for troubleshooting
        x_range_ft = np.ptp(positions_ft[:, 0])
        y_range_ft = np.ptp(positions_ft[:, 1])
        z_range_ft = np.ptp(positions_ft[:, 2])
        total_path_ft = np.sum(np.linalg.norm(np.diff(positions_ft, axis=0), axis=1))
        max_jump = np.max(np.linalg.norm(np.diff(positions_ft, axis=0), axis=1)) if len(positions_ft) > 1 else 0
        
        # Get address position in feet for display
        address_idx = self.address_idx if hasattr(self, 'address_idx') else 0
        if start_idx <= address_idx <= end_idx:
            # Address is in visible range
            address_visible = True
            address_pos_ft = positions_ft[address_idx - start_idx]
        else:
            address_visible = False
            address_pos_ft = positions_ft[0]  # Fallback
        
        # Build diagnostic text with address and optional impact data
        diag_text = (f'📍 ADDRESS POSITION:\n'
                    f'  X: {address_pos_ft[0]:+.2f} ft\n'
                    f'  Y: {address_pos_ft[1]:+.2f} ft\n'
                    f'  Z: {address_pos_ft[2]:+.2f} ft\n'
                    f'  Face: {self.face_angles[address_idx]:+.1f}°\n'
                    f'\nTrajectory Ranges:\n'
                    f'  Target Line (X): {x_range_ft:.2f} ft\n'
                    f'  In/Out (Y): {y_range_ft:.2f} ft\n'
                    f'  Height (Z): {z_range_ft:.2f} ft\n'
                    f'Total Path: {total_path_ft:.1f} ft\n'
                    f'Max Jump: {max_jump:.2f} ft')
        
        # Add impact data if available
        if impact_data is not None:
            impact_text = (f'\n\n★ IMPACT DATA ★\n'
                          f'Position:\n'
                          f'  X: {impact_data["pos"][0]:+.2f} ft\n'
                          f'  Y: {impact_data["pos"][1]:+.2f} ft\n'
                          f'  Z: {impact_data["pos"][2]:+.2f} ft\n'
                          f'Speed: {impact_data["speed"]:.1f} mph\n'
                          f'Face: {impact_data["angle"]:+.1f}°')
            diag_text += impact_text
        
        ax.text2D(0.02, 0.98, diag_text, transform=ax.transAxes, 
                 fontsize=9, verticalalignment='top', family='monospace',
                 bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8, 
                          edgecolor='gray', linewidth=1))
        
        # Place legend in lower left to avoid overlap with diagnostic text in upper left
        ax.legend(loc='lower left', fontsize=8, framealpha=0.9)
        
        # Add colorbar with speed in mph on the left side
        # Create colorbar with converted values
        cbar = plt.colorbar(scatter, ax=ax, pad=0.1, shrink=0.8, location='left')
        cbar.set_label('Speed (mph)', rotation=90, labelpad=15)
        # Update colorbar ticks to show mph
        ticks = cbar.get_ticks()
        cbar.set_ticks(ticks)
        cbar.set_ticklabels([f'{t * self.rad_to_mph:.1f}' for t in ticks])
        
    def plot_speed(self, ax, start_idx=None, end_idx=None):
        """Plot speed over time
        
        Args:
            ax: Axis to plot on
            start_idx: Starting sample index (default: 0)
            end_idx: Ending sample index (default: len-1)
        """
        if start_idx is None:
            start_idx = 0
        if end_idx is None:
            end_idx = len(self.velocities) - 1
        
        # Filter data to selected range
        velocities = self.velocities[start_idx:end_idx+1]
        time = np.arange(start_idx, end_idx+1)
        
        # Convert to mph for display
        velocities_mph = velocities * self.rad_to_mph
        ax.plot(time, velocities_mph, 'b-', linewidth=2)
        ax.fill_between(time, velocities_mph, alpha=0.3)
        
        # Mark maximum speed or impact (if within visible range)
        if self.impact_idx is not None and start_idx <= self.impact_idx <= end_idx:
            # Mark impact point
            relative_impact_idx = self.impact_idx - start_idx
            impact_speed = velocities[relative_impact_idx] * self.rad_to_mph
            ax.plot(self.impact_idx, impact_speed, 
                   'go', markersize=15, markeredgewidth=2, 
                   markeredgecolor='orange', label=f'Impact: {impact_speed:.1f} mph',
                   zorder=10)
            ax.axvline(self.impact_idx, color='orange', linestyle='--', alpha=0.5, linewidth=2)
        else:
            # Just mark max speed in visible range
            max_idx = np.argmax(velocities_mph)
            actual_idx = start_idx + max_idx
            ax.plot(actual_idx, velocities_mph[max_idx], 'ro', markersize=10, 
                   label=f'Max: {velocities_mph[max_idx]:.1f} mph')
        
        ax.set_xlabel('Sample Number')
        ax.set_ylabel('Speed (mph)')
        ax.set_title('Club Head Speed')
        ax.grid(True, alpha=0.3)
        ax.legend()
    
    def plot_face_angle(self, ax, start_idx=None, end_idx=None):
        """Plot club face angle relative to target line over time
        
        Args:
            ax: Axis to plot on
            start_idx: Starting sample index (default: 0)
            end_idx: Ending sample index (default: len-1)
        """
        if start_idx is None:
            start_idx = 0
        if end_idx is None:
            end_idx = len(self.face_angles) - 1
        
        # Filter data to selected range
        face_angles = self.face_angles[start_idx:end_idx+1]
        time = np.arange(start_idx, end_idx+1)
        
        # Plot face angle
        ax.plot(time, face_angles, 'g-', linewidth=2, label='Face Angle')
        ax.fill_between(time, face_angles, alpha=0.2, color='green')
        
        # Add reference line at 0° (square to target)
        ax.axhline(y=0, color='black', linestyle='--', alpha=0.5, linewidth=2, label='Square (0°)')
        
        # Mark setup position (first sample)
        setup_angle = face_angles[0]
        ax.plot(start_idx, setup_angle, 'bo', markersize=10, 
               label=f'Setup: {setup_angle:.1f}°', zorder=10)
        
        # Mark impact (if detected and within visible range)
        if self.impact_idx is not None and start_idx <= self.impact_idx <= end_idx:
            relative_impact_idx = self.impact_idx - start_idx
            impact_angle = face_angles[relative_impact_idx]
            ax.plot(self.impact_idx, impact_angle, 
                   'ro', markersize=15, markeredgewidth=2, 
                   markeredgecolor='orange', label=f'Impact: {impact_angle:.1f}°',
                   zorder=10)
            ax.axvline(self.impact_idx, color='orange', linestyle='--', alpha=0.5, linewidth=2)
        
        # Shade regions for open/closed face
        y_min, y_max = ax.get_ylim()
        ax.fill_between([start_idx, end_idx+1], 0, y_max, alpha=0.1, color='blue', 
                        label='Closed (Left)')
        ax.fill_between([start_idx, end_idx+1], y_min, 0, alpha=0.1, color='red', 
                        label='Open (Right)')
        
        ax.set_xlabel('Sample Number')
        ax.set_ylabel('Face Angle (degrees)')
        ax.set_title('Club Face Angle vs Target Line\n(+Closed / -Open)')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7, loc='upper right')
        
    def plot_top_view(self, ax, start_idx=None, end_idx=None):
        """Plot top-down view (X-Y plane: target line and in/out)
        
        Args:
            ax: Axis to plot on
            start_idx: Starting sample index (default: 0)
            end_idx: Ending sample index (default: len-1)
        """
        if start_idx is None:
            start_idx = 0
        if end_idx is None:
            end_idx = len(self.positions) - 1
        
        # Filter data to selected range
        positions = self.positions[start_idx:end_idx+1]
        velocities = self.velocities[start_idx:end_idx+1]
        
        # Convert positions to feet
        positions_ft = positions * self.m_to_ft
        
        scatter = ax.scatter(
            positions_ft[:, 0],  # X: target line
            positions_ft[:, 1],  # Y: in/out
            c=velocities,
            cmap='RdYlGn_r',
            s=30,
            alpha=0.6
        )
        
        ax.plot(positions_ft[:, 0], positions_ft[:, 1], 'b-', alpha=0.8, linewidth=2)
        ax.scatter(positions_ft[0, 0], positions_ft[0, 1], color='green', s=100, marker='o', 
                  label=f'Start (#{start_idx})')
        ax.scatter(positions_ft[-1, 0], positions_ft[-1, 1], color='red', s=100, marker='X', 
                  label=f'End (#{end_idx})')
        
        # Mark impact and ball if detected and within visible range
        if self.impact_idx is not None and start_idx <= self.impact_idx <= end_idx:
            relative_impact_idx = self.impact_idx - start_idx
            impact_pos = positions_ft[relative_impact_idx]
            
            # Ball marker
            ax.scatter(impact_pos[0], impact_pos[1], 
                      color='white', s=150, marker='o', 
                      edgecolors='black', linewidths=3, label='Ball', zorder=12)
            
            # Impact marker
            ax.scatter(impact_pos[0], impact_pos[1], 
                      color='gold', s=250, marker='*', 
                      edgecolors='orange', linewidths=2,
                      label=f'Impact (#{self.impact_idx})', zorder=10)
        
        # Add orientation arrows (sample from filtered range)
        orientations = self.orientations[start_idx:end_idx+1]
        step = max(1, len(positions_ft) // 15)
        for i in range(0, len(positions_ft), step):
            quat = orientations[i]
            forward = _rotate_vector_by_quaternion_wxyz(quat, [0.0, 0.0, 0.0167]) * self.m_to_ft
            pos = positions_ft[i]
            
            # Map to golf coordinates for display
            forward_golf = np.array([forward[1], forward[2], forward[0]])
            
            ax.annotate('',
                xy=(pos[0] + forward_golf[0], pos[1] + forward_golf[1]),
                xytext=(pos[0], pos[1]),
                arrowprops=dict(arrowstyle='->', color='red', lw=1, alpha=0.5)
            )
        
        ax.set_xlabel('Target Line (X-axis, feet)\n← Left | Right →', fontsize=9, fontweight='bold')
        ax.set_ylabel('In/Out (Y-axis, feet)\n← Ball | Away →', fontsize=9, fontweight='bold')
        ax.set_title('Top View: Target Line vs In/Out\n(Looking down from above)', fontsize=10, fontweight='bold')
        
        # Dynamic axis limits with padding
        x_min_ft, x_max_ft = np.min(positions_ft[:, 0]), np.max(positions_ft[:, 0])
        y_min_ft, y_max_ft = np.min(positions_ft[:, 1]), np.max(positions_ft[:, 1])
        x_padding = max(0.5, (x_max_ft - x_min_ft) * 0.2)
        y_padding = max(0.5, (y_max_ft - y_min_ft) * 0.2)
        
        ax.set_xlim(x_min_ft - x_padding, x_max_ft + x_padding)
        ax.set_ylim(y_min_ft - y_padding, y_max_ft + y_padding)
        # ax.set_aspect('equal')  # Disabled to accommodate extended target line range
        ax.grid(True, alpha=0.3)
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=7, framealpha=0.9)
        
    def plot_side_view(self, ax, start_idx=None, end_idx=None):
        """Plot side view (Y-Z plane: in/out and height)
        
        Args:
            ax: Axis to plot on
            start_idx: Starting sample index (default: 0)
            end_idx: Ending sample index (default: len-1)
        """
        if start_idx is None:
            start_idx = 0
        if end_idx is None:
            end_idx = len(self.positions) - 1
        
        # Filter data to selected range
        positions = self.positions[start_idx:end_idx+1]
        velocities = self.velocities[start_idx:end_idx+1]
        
        # Convert positions to feet
        positions_ft = positions * self.m_to_ft
        
        scatter = ax.scatter(
            positions_ft[:, 1],  # Y: in/out
            positions_ft[:, 2],  # Z: height
            c=velocities,
            cmap='RdYlGn_r',
            s=30,
            alpha=0.6
        )
        
        ax.plot(positions_ft[:, 1], positions_ft[:, 2], 'b-', alpha=0.8, linewidth=2)
        ax.scatter(positions_ft[0, 1], positions_ft[0, 2], color='green', s=100, marker='o', 
                  label=f'Start (#{start_idx})')
        ax.scatter(positions_ft[-1, 1], positions_ft[-1, 2], color='red', s=100, marker='X', 
                  label=f'End (#{end_idx})')
        
        # Mark impact and ball if detected and within visible range
        if self.impact_idx is not None and start_idx <= self.impact_idx <= end_idx:
            relative_impact_idx = self.impact_idx - start_idx
            impact_pos = positions_ft[relative_impact_idx]
            
            # Ball marker
            ax.scatter(impact_pos[1], impact_pos[2], 
                      color='white', s=150, marker='o', 
                      edgecolors='black', linewidths=3, label='Ball', zorder=12)
            
            # Impact marker
            ax.scatter(impact_pos[1], impact_pos[2], 
                      color='gold', s=250, marker='*', 
                      edgecolors='orange', linewidths=2,
                      label=f'Impact (#{self.impact_idx})', zorder=10)
        
        ax.set_xlabel('In/Out (Y-axis, feet)\n← Ball | Away →', fontsize=9, fontweight='bold')
        ax.set_ylabel('Height (Z-axis, feet)\n← Ground | Up →', fontsize=9, fontweight='bold')
        ax.set_title('Side View: In/Out vs Height\n(Looking from target line)', fontsize=10, fontweight='bold')
        
        # Dynamic axis limits with padding
        y_min_ft, y_max_ft = np.min(positions_ft[:, 1]), np.max(positions_ft[:, 1])
        z_min_ft, z_max_ft = np.min(positions_ft[:, 2]), np.max(positions_ft[:, 2])
        y_padding = max(0.5, (y_max_ft - y_min_ft) * 0.2)
        z_padding = max(0.5, (z_max_ft - z_min_ft) * 0.2)
        z_min_display = 0 if z_min_ft < 1.0 else z_min_ft - z_padding
        
        ax.set_xlim(y_min_ft - y_padding, y_max_ft + y_padding)
        ax.set_ylim(z_min_display, z_max_ft + z_padding)
        ax.axhline(y=0, color='blue', linestyle='--', alpha=0.3, linewidth=1)  # Ground level
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=7, framealpha=0.9)


# Test function
if __name__ == "__main__":
    # Generate sample data for testing
    import math
    
    test_data = []
    for i in range(100):
        t = i / 100.0 * 2 * math.pi
        # Simulate a swing motion
        angle = t
        axis = np.array([0.0, 1.0, 0.0])
        quat_wxyz = _rotvec_to_quat_wxyz(angle * axis)
        
        test_data.append({
            'q0': quat_wxyz[0],  # w
            'q1': quat_wxyz[1],  # x
            'q2': quat_wxyz[2],  # y
            'q3': quat_wxyz[3],  # z
            'timestamp': i * 0.02
        })
    
    visualizer = SwingVisualizer(test_data)
    visualizer.show()
