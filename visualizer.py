"""
3D Visualization Module for Golf Swing Analysis
Displays club head path, speed, and face direction
"""

import numpy as np
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
                 filename=None, club_length_m=1.168):
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
        
        # Build full trajectory by integrating club position through space
        # Use club length to convert angular motion to linear club head position
        position = np.array([0.0, 0.0, 0.0])
        prev_quat = None
        
        for i, point in enumerate(self.data):
            quat = _normalize_quaternion_wxyz(np.array([point['q0'], point['q1'], point['q2'], point['q3']]))
            speed = smoothed_speeds[i]
            
            if prev_quat is not None:
                # Calculate rotation vector between samples
                rotvec = _quat_delta_rotvec_wxyz(prev_quat, quat)
                
                # Apply deadband to filter very small movements
                if np.linalg.norm(rotvec) > self.deadband_rad:
                    # Get the club head position vector (pointing down the shaft)
                    # Natural golf coordinates: X=target line, Y=in/out, Z=height
                    if self.coordinate_system == 'ground':
                        # Club shaft direction (club_length down the shaft from grip)
                        club_vector = _rotate_vector_by_quaternion_wxyz(quat, [0.0, 0.0, self.club_length_m])
                        # Map sensor frame to natural golf coordinates:
                        # Sensor X → Golf Z (height, INVERTED), Sensor Y → Golf X (target), Sensor Z → Golf Y (in/out)
                        club_head_pos = np.array([club_vector[1], club_vector[2], -club_vector[0]])
                    else:
                        # Club frame: X=up shaft
                        club_head_pos = _rotate_vector_by_quaternion_wxyz(quat, [self.club_length_m, 0.0, 0.0])
                    
                    # Update position to club head location
                    position = club_head_pos
            
            self.velocities.append(speed)
            self.positions.append(position.copy())
            prev_quat = quat
            
        self.positions = np.array(self.positions)
        self.velocities = np.array(self.velocities)
        
        # Detect impact point (maximum speed with deceleration)
        self.impact_idx = None
        if len(self.velocities) > 10:
            max_speed_idx = np.argmax(self.velocities)
            max_speed_mph = self.velocities[max_speed_idx] * self.rad_to_mph
            
            # Check for deceleration after peak (characteristic of ball contact)
            if max_speed_idx < len(self.velocities) - 10:
                post_impact_speeds = self.velocities[max_speed_idx:max_speed_idx+10] * self.rad_to_mph
                speed_drop = max_speed_mph - np.min(post_impact_speeds)
                
                # If speed drops by >10 mph within 0.1s, likely ball contact
                if speed_drop > 10:
                    self.impact_idx = max_speed_idx
                    print(f"✓ Impact detected at sample #{max_speed_idx} ({max_speed_mph:.1f} mph)")
        
        # Normalize position based on impact point (X, Y, Z)
        # This centers the visualization on the ball position
        if len(self.positions) > 0 and self.impact_idx is not None:
            impact_pos = self.positions[self.impact_idx].copy()
            
            # Set impact X (target line) to 0
            self.positions[:, 0] -= impact_pos[0]
            
            # Set impact Y (in/out) to 0
            self.positions[:, 1] -= impact_pos[1]
            
            # Set impact Z (height) to 0.7 ft (driver on tee)
            target_impact_height = 0.7 / self.m_to_ft  # 0.7 ft in meters
            height_offset = target_impact_height - impact_pos[2]
            self.positions[:, 2] += height_offset
            
            print(f"✓ Impact normalized to origin: (0, 0, 0.7 ft)")
        elif len(self.positions) > 0:
            # Fallback: normalize based on address if no impact detected
            address_pos = self.positions[0].copy()
            self.positions[:, 0] -= address_pos[0]
            self.positions[:, 1] -= address_pos[1]
            target_address_height = 0.5 / self.m_to_ft
            height_offset = target_address_height - address_pos[2]
            self.positions[:, 2] += height_offset
        
        # Print diagnostic information
        print(f"\n=== Swing Data Analysis (Natural Golf Coordinates) ===")
        print(f"Total samples: {len(self.data)}")
        print(f"Position points: {len(self.positions)}")
        print(f"Max speed: {np.max(self.velocities):.2f} rad/s ({np.max(self.velocities) * self.rad_to_mph:.1f} mph)")
        print(f"Position range - Target Line (X): {np.min(self.positions[:, 0]):.3f} to {np.max(self.positions[:, 0]):.3f} m ({np.ptp(self.positions[:, 0]) * self.m_to_ft:.2f} ft)")
        print(f"Position range - In/Out (Y):      {np.min(self.positions[:, 1]):.3f} to {np.max(self.positions[:, 1]):.3f} m ({np.ptp(self.positions[:, 1]) * self.m_to_ft:.2f} ft)")
        print(f"Position range - Height (Z):      {np.min(self.positions[:, 2]):.3f} to {np.max(self.positions[:, 2]):.3f} m ({np.ptp(self.positions[:, 2]) * self.m_to_ft:.2f} ft)")
        total_distance = np.sum(np.linalg.norm(np.diff(self.positions, axis=0), axis=1))
        print(f"Total path length: {total_distance:.3f} m ({total_distance * self.m_to_ft:.2f} ft)")
        print("="*60)
        
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
        fig = plt.figure(figsize=(16, 10))
        fig.canvas.manager.set_window_title(display_name)
        fig.suptitle(filter_info, fontsize=10, y=0.995)
        
        # Create custom grid: 3D plot takes left 2/3, other plots on right 1/3
        # Leave space at bottom for slider controls and scale
        gs = GridSpec(3, 2, figure=fig, width_ratios=[2, 1], height_ratios=[1, 1, 1],
                     hspace=0.5, wspace=0.3, top=0.96, bottom=0.17, left=0.05, right=0.98)
        
        # 3D trajectory plot - spans all 3 rows on the left (200% larger)
        ax1 = fig.add_subplot(gs[:, 0], projection='3d')
        
        # Speed over time - top right
        ax2 = fig.add_subplot(gs[0, 1])
        
        # Top view - middle right
        ax3 = fig.add_subplot(gs[1, 1])
        
        # Side view - bottom right
        ax4 = fig.add_subplot(gs[2, 1])
        
        # Store axes for update function
        self.fig = fig
        self.axes = {'3d': ax1, 'speed': ax2, 'top': ax3, 'side': ax4}
        
        # Create slider axes at bottom with proper spacing
        ax_slider_start = fig.add_axes([0.15, 0.11, 0.65, 0.02])
        ax_slider_end = fig.add_axes([0.15, 0.03, 0.65, 0.02])
        
        # Create sliders
        total_samples = len(self.positions)
        self.slider_start = Slider(ax_slider_start, 'Start Sample', 0, total_samples-1, 
                                   valinit=0, valstep=1, color='lightblue')
        self.slider_end = Slider(ax_slider_end, 'End Sample', 0, total_samples-1, 
                                 valinit=total_samples-1, valstep=1, color='lightblue')
        
        # Add scale indicator between sliders
        ax_scale = fig.add_axes([0.15, 0.067, 0.65, 0.015])
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
        ax_btn_reset = fig.add_axes([0.82, 0.03, 0.08, 0.04])
        btn_reset = Button(ax_btn_reset, 'Reset', color='lightgray', hovercolor='gray')
        
        def reset(event):
            self.slider_start.set_val(0)
            self.slider_end.set_val(total_samples-1)
        
        btn_reset.on_clicked(reset)
        
        # Focus Impact button (if impact detected, aligned with start slider)
        if self.impact_idx is not None:
            ax_btn_impact = fig.add_axes([0.82, 0.11, 0.17, 0.04])
            btn_impact = Button(ax_btn_impact, 'Impact', color='gold', hovercolor='orange')
            
            def focus_impact(event):
                # Show ±50 samples around impact
                impact_start = max(0, self.impact_idx - 50)
                impact_end = min(total_samples-1, self.impact_idx + 50)
                self.slider_start.set_val(impact_start)
                self.slider_end.set_val(impact_end)
            
            btn_impact.on_clicked(focus_impact)
        
        # Plot all views with full range initially
        self.plot_trajectory(ax1, 0, total_samples-1)
        self.plot_speed(ax2, 0, total_samples-1)
        self.plot_top_view(ax3, 0, total_samples-1)
        self.plot_side_view(ax4, 0, total_samples-1)
        
        plt.tight_layout()
        
        # Maximize and bring window to front
        fig.canvas.manager.window.state('zoomed')
        try:
            # Try to bring the matplotlib window to the front
            fig.canvas.manager.window.lift()
            fig.canvas.manager.window.attributes('-topmost', True)
            fig.canvas.manager.window.after_idle(fig.canvas.manager.window.attributes, '-topmost', False)
            fig.canvas.manager.window.focus_force()
        except:
            pass  # If these methods don't work, just continue
        
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
        ax.scatter(*positions_ft[0], color='green', s=100, marker='o', 
                  label=f'Start (#{start_idx})', zorder=10)
        ax.scatter(*positions_ft[-1], color='red', s=100, marker='X', 
                  label=f'End (#{end_idx})', zorder=10)
        
        # Mark ball position at origin (0, 0, ground level)
        ax.scatter(0, 0, 0, color='white', s=150, marker='o', 
                  edgecolors='black', linewidths=3, label='Ball', zorder=12)
        
        # Mark impact point if detected and within visible range
        if self.impact_idx is not None and start_idx <= self.impact_idx <= end_idx:
            relative_impact_idx = self.impact_idx - start_idx
            impact_pos = positions_ft[relative_impact_idx]
            impact_speed = velocities[relative_impact_idx] * self.rad_to_mph
            ax.scatter(impact_pos[0], impact_pos[1], impact_pos[2], 
                      color='gold', s=400, marker='*', 
                      edgecolors='orange', linewidths=2,
                      label=f'Impact (#{self.impact_idx}, {impact_speed:.1f} mph)', zorder=15)
            # Add impact label
            ax.text(impact_pos[0], impact_pos[1], impact_pos[2] + 0.2, 
                   'IMPACT', fontsize=12, fontweight='bold', 
                   color='orange', ha='center', zorder=16)
        
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
        
        # Set axis limits with padding to contain arrows
        padding = arrow_scale * 1.5
        x_min, x_max = positions_ft[:, 0].min() - padding, positions_ft[:, 0].max() + padding
        y_min, y_max = positions_ft[:, 1].min() - padding, positions_ft[:, 1].max() + padding
        z_min, z_max = positions_ft[:, 2].min() - padding, positions_ft[:, 2].max() + padding
        
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)
        ax.set_zlim(max(z_min, -1), z_max)  # Don't go too far underground
        
        # Draw ground plane (X-Y plane at Z=0) to emphasize floor
        if self.coordinate_system == 'ground':
            from matplotlib.patches import Rectangle
            from mpl_toolkits.mplot3d import art3d
            
            # Create a semi-transparent ground plane
            ground_x = [x_min, x_max, x_max, x_min, x_min]
            ground_y = [y_min, y_min, y_max, y_max, y_min]
            ground_z = [0, 0, 0, 0, 0]
            ax.plot(ground_x, ground_y, ground_z, 'k-', alpha=0.3, linewidth=1)
            
            # Add grid on ground plane
            for x_grid in np.linspace(x_min, x_max, 5):
                ax.plot([x_grid, x_grid], [y_min, y_max], [0, 0], 'k-', alpha=0.1, linewidth=0.5)
            for y_grid in np.linspace(y_min, y_max, 5):
                ax.plot([x_min, x_max], [y_grid, y_grid], [0, 0], 'k-', alpha=0.1, linewidth=0.5)
        
        # Set labels for natural golf coordinate system
        if self.coordinate_system == 'ground':
            ax.set_xlabel('Target Line (ft)', fontsize=10, fontweight='bold')
            ax.set_ylabel('In/Out (ft)', fontsize=10, fontweight='bold')
            ax.set_zlabel('Height (ft)', fontsize=10, fontweight='bold')
            ax.set_title('3D Club Head Trajectory\n(Ball at origin, Ground at Z=0)', fontsize=11, fontweight='bold')
        else:
            ax.set_xlabel('Shaft (ft)')
            ax.set_ylabel('Face Normal (ft)')
            ax.set_zlabel('Toe/Heel (ft)')
            ax.set_title('3D Club Head Trajectory\n(Red arrows = velocity direction)')
        
        # Set viewing angle to look DOWN at the ground plane
        # elev=20 looks down from above, azim=-60 gives good 3/4 view
        ax.view_init(elev=20, azim=-60, roll=0)
        
        ax.legend(loc='upper left')
        
        # Add colorbar with speed in mph
        # Create colorbar with converted values
        cbar = plt.colorbar(scatter, ax=ax, pad=0.1, shrink=0.8)
        cbar.set_label('Speed (mph)')
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
        
        # Mark ball at origin
        ax.scatter(0, 0, color='white', s=150, marker='o', 
                  edgecolors='black', linewidths=3, label='Ball', zorder=12)
        
        # Mark impact if detected and within visible range
        if self.impact_idx is not None and start_idx <= self.impact_idx <= end_idx:
            relative_impact_idx = self.impact_idx - start_idx
            impact_pos = positions_ft[relative_impact_idx]
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
        
        ax.set_xlabel('Target Line (ft)')
        ax.set_ylabel('In/Out (ft)')
        ax.set_title('Top View\n(Ball at origin)', fontsize=10)
        ax.set_aspect('equal')
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
        
        # Mark ball at ground level (origin on this view is at Y=0, Z=0)
        ax.scatter(0, 0, color='white', s=150, marker='o', 
                  edgecolors='black', linewidths=3, label='Ball', zorder=12)
        
        # Mark impact if detected and within visible range
        if self.impact_idx is not None and start_idx <= self.impact_idx <= end_idx:
            relative_impact_idx = self.impact_idx - start_idx
            impact_pos = positions_ft[relative_impact_idx]
            ax.scatter(impact_pos[1], impact_pos[2], 
                      color='gold', s=250, marker='*', 
                      edgecolors='orange', linewidths=2,
                      label=f'Impact (#{self.impact_idx})', zorder=10)
        
        ax.set_xlabel('In/Out (ft)')
        ax.set_ylabel('Height (ft)')
        ax.set_title('Side View\n(Ball at Y=0, ground)', fontsize=10)
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
