"""
3D Visualization Module for Golf Swing Analysis
Displays club head path, speed, and face direction
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
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
                 filename=None):
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
        
        self.process_data()
        
    def process_data(self):
        """Convert quaternion data to positions and velocities"""
        # Simulate position by integrating orientation changes
        # In a real application, you might use double integration of accelerometer data
        
        position = np.array([0.0, 0.0, 0.0])
        prev_quat = None
        raw_speeds = []
        
        for i, point in enumerate(self.data):
            # Extract quaternion
            quat = _normalize_quaternion_wxyz(np.array([point['q0'], point['q1'], point['q2'], point['q3']]))
            
            # Store orientation
            self.orientations.append(quat)
            
            # Calculate movement direction from rotation change
            if prev_quat is not None:
                # Rotation difference as a rotation vector.
                rotvec = _quat_delta_rotvec_wxyz(prev_quat, quat)
                
                # Use rotation vector magnitude as speed indicator
                speed = np.linalg.norm(rotvec)
                if speed < self.deadband_rad:
                    speed = 0.0
                raw_speeds.append(speed)
            else:
                raw_speeds.append(0.0)
                
            prev_quat = quat
        
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
        
        # Apply speed threshold - ignore very small rotations (noise floor)
        speed_threshold = np.percentile(smoothed_speeds, self.noise_floor_percentile)
        
        # Rebuild positions with smoothed data
        position = np.array([0.0, 0.0, 0.0])
        for i, point in enumerate(self.data):
            quat = _normalize_quaternion_wxyz(np.array([point['q0'], point['q1'], point['q2'], point['q3']]))
            
            speed = smoothed_speeds[i]
            
            # Only move if speed exceeds noise threshold
            if speed > speed_threshold:
                # Determine forward direction based on coordinate system
                if self.coordinate_system == 'ground':
                    # Ground frame: X=left/right (target line), Y=up/down, Z=in/out from golfer
                    # At address: Cal Z (face normal) points along target line (User X)
                    # Use face normal as forward direction along X-axis
                    face_direction = _rotate_vector_by_quaternion_wxyz(quat, [0.0, 0.0, 1.0])  # Cal Z = face normal
                    # Project to user coordinate frame: face_direction becomes X-movement
                    forward = np.array([face_direction[2], face_direction[0], face_direction[1]])
                else:
                    # Club frame: X=up shaft, Y=toe-heel, Z=face normal
                    forward = _rotate_vector_by_quaternion_wxyz(quat, [1.0, 0.0, 0.0])  # Use shaft direction as forward
                    
                position = position + forward * speed * 0.05  # Reduced scale factor (was 0.1)
            
            self.velocities.append(speed)
            self.positions.append(position.copy())
            
        self.positions = np.array(self.positions)
        self.velocities = np.array(self.velocities)
        
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
        
        fig = plt.figure()
        fig.canvas.manager.set_window_title(display_name)
        fig.suptitle(filter_info, fontsize=10, y=0.995)
        
        # 3D trajectory plot
        ax1 = fig.add_subplot(2, 2, 1, projection='3d')
        self.plot_trajectory(ax1)
        
        # Speed over time
        ax2 = fig.add_subplot(2, 2, 2)
        self.plot_speed(ax2)
        
        # Top view (X-Y plane)
        ax3 = fig.add_subplot(2, 2, 3)
        self.plot_top_view(ax3)
        
        # Side view (X-Z plane)
        ax4 = fig.add_subplot(2, 2, 4)
        self.plot_side_view(ax4)
        
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
        
    def plot_trajectory(self, ax):
        """Plot 3D trajectory with color-coded speed"""
        # Normalize velocities for colormap
        norm_vel = self.velocities / (np.max(self.velocities) + 1e-6)
        
        # Plot trajectory
        scatter = ax.scatter(
            self.positions[:, 0],
            self.positions[:, 1],
            self.positions[:, 2],
            c=self.velocities,
            cmap='RdYlGn_r',
            s=5,
            alpha=0.6
        )
        
        # Add line
        ax.plot(
            self.positions[:, 0],
            self.positions[:, 1],
            self.positions[:, 2],
            'b-',
            alpha=0.3,
            linewidth=1
        )
        
        # Mark start and end
        ax.scatter(*self.positions[0], color='green', s=100, marker='o', label='Start', zorder=10)
        ax.scatter(*self.positions[-1], color='red', s=100, marker='X', label='End', zorder=10)
        
        # Calculate trajectory bounds for arrow scaling
        x_range = np.ptp(self.positions[:, 0]) if len(self.positions) > 1 else 1.0
        y_range = np.ptp(self.positions[:, 1]) if len(self.positions) > 1 else 1.0
        z_range = np.ptp(self.positions[:, 2]) if len(self.positions) > 1 else 1.0
        avg_range = (x_range + y_range + z_range) / 3.0
        arrow_scale = max(0.02, avg_range * 0.2)  # Scale arrows to 20% of average range
        
        # Add velocity direction arrows at key points
        step = max(1, len(self.positions) // 10)  # Max 10 arrows
        for i in range(step, len(self.positions) - step, step):  # Skip first/last to calculate velocity
            # Calculate velocity direction from neighboring positions
            velocity_vec = self.positions[i + step] - self.positions[i - step]
            vel_magnitude = np.linalg.norm(velocity_vec)
            
            if vel_magnitude > 1e-6:  # Only show if there's actual movement
                # Normalize and scale velocity vector for arrow
                velocity_direction = (velocity_vec / vel_magnitude) * arrow_scale
                pos = self.positions[i]
                
                ax.quiver(
                    pos[0], pos[1], pos[2],
                    velocity_direction[0], velocity_direction[1], velocity_direction[2],
                    color='darkred', alpha=0.6, arrow_length_ratio=0.8, linewidth=2.5
                )
        
        # Set axis limits with padding to contain arrows
        padding = arrow_scale * 1.5
        ax.set_xlim(self.positions[:, 0].min() - padding, self.positions[:, 0].max() + padding)
        ax.set_ylim(self.positions[:, 1].min() - padding, self.positions[:, 1].max() + padding)
        ax.set_zlim(self.positions[:, 2].min() - padding, self.positions[:, 2].max() + padding)
        
        # Set labels based on coordinate system
        if self.coordinate_system == 'ground':
            ax.set_xlabel('X - Target Line (m)')
            ax.set_ylabel('Y - Height (m)')
            ax.set_zlabel('Z - In/Out (m)')
            ax.set_title('3D Club Head Trajectory\n(Red arrows = velocity direction)')
        else:
            ax.set_xlabel('X - Shaft (m)')
            ax.set_ylabel('Y - Toe/Heel (m)')
            ax.set_zlabel('Z - Face Normal (m)')
            ax.set_title('3D Club Head Trajectory\n(Red arrows = velocity direction)')
        ax.legend(loc='upper left')
        
        # Add colorbar
        cbar = plt.colorbar(scatter, ax=ax, pad=0.1, shrink=0.8)
        cbar.set_label('Angular Speed (rad/s)')
        
    def plot_speed(self, ax):
        """Plot speed over time"""
        time = np.arange(len(self.velocities))
        ax.plot(time, self.velocities, 'b-', linewidth=2)
        ax.fill_between(time, self.velocities, alpha=0.3)
        
        # Mark maximum speed
        max_idx = np.argmax(self.velocities)
        ax.plot(max_idx, self.velocities[max_idx], 'ro', markersize=10, label=f'Max: {self.velocities[max_idx]:.3f} rad/s')
        
        ax.set_xlabel('Sample Number')
        ax.set_ylabel('Angular Speed (rad/s)')
        ax.set_title('Club Head Speed')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
    def plot_top_view(self, ax):
        """Plot top-down view (X-Y plane)"""
        scatter = ax.scatter(
            self.positions[:, 0],
            self.positions[:, 1],
            c=self.velocities,
            cmap='RdYlGn_r',
            s=30,
            alpha=0.6
        )
        
        ax.plot(self.positions[:, 0], self.positions[:, 1], 'b-', alpha=0.3, linewidth=1)
        ax.scatter(self.positions[0, 0], self.positions[0, 1], color='green', s=100, marker='o', label='Start')
        ax.scatter(self.positions[-1, 0], self.positions[-1, 1], color='red', s=100, marker='X', label='End')
        
        # Add orientation arrows
        step = max(1, len(self.positions) // 15)
        for i in range(0, len(self.positions), step):
            quat = self.orientations[i]
            forward = _rotate_vector_by_quaternion_wxyz(quat, [0.0, 0.0, 0.15])
            pos = self.positions[i]
            
            ax.arrow(
                pos[0], pos[1],
                forward[0], forward[1],
                head_width=0.025, head_length=0.025,
                fc='red', ec='red', alpha=0.5
            )
        
        ax.set_xlabel('X (m)')
        ax.set_ylabel('Y (m)')
        ax.set_title('Top View (X-Y Plane)')
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
    def plot_side_view(self, ax):
        """Plot side view (X-Z plane)"""
        scatter = ax.scatter(
            self.positions[:, 0],
            self.positions[:, 2],
            c=self.velocities,
            cmap='RdYlGn_r',
            s=30,
            alpha=0.6
        )
        
        ax.plot(self.positions[:, 0], self.positions[:, 2], 'b-', alpha=0.3, linewidth=1)
        ax.scatter(self.positions[0, 0], self.positions[0, 2], color='green', s=100, marker='o', label='Start')
        ax.scatter(self.positions[-1, 0], self.positions[-1, 2], color='red', s=100, marker='X', label='End')
        
        ax.set_xlabel('X (m)')
        ax.set_ylabel('Z (m)')
        ax.set_title('Side View (X-Z Plane)')
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.legend()


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
