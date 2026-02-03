"""
3D Visualization Module for Golf Swing Analysis
Displays club head path, speed, and face direction
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from mpl_toolkits.mplot3d import Axes3D
from scipy.spatial.transform import Rotation as R


class SwingVisualizer:
    def __init__(self, data, coordinate_system='ground'):
        """
        Initialize visualizer with quaternion data
        
        Parameters:
        -----------
        data: list of dictionaries with keys 'q0', 'q1', 'q2', 'q3', 'timestamp'
        coordinate_system: str
            'ground' - X=left/right (target line), Y=up/down, Z=in/out (toward/away from golfer) (default)
            'club' - X=up shaft, Y=toe-heel, Z=face normal
        """
        self.data = data
        self.positions = []
        self.velocities = []
        self.orientations = []
        self.coordinate_system = coordinate_system
        
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
            quat = np.array([point['q0'], point['q1'], point['q2'], point['q3']])
            
            # Store orientation
            self.orientations.append(quat)
            
            # Calculate movement direction from rotation change
            if prev_quat is not None:
                # Get rotation from previous to current orientation
                r_prev = R.from_quat([prev_quat[1], prev_quat[2], prev_quat[3], prev_quat[0]])
                r_curr = R.from_quat([quat[1], quat[2], quat[3], quat[0]])
                
                # Rotation difference
                r_diff = r_curr * r_prev.inv()
                rotvec = r_diff.as_rotvec()
                
                # Use rotation vector magnitude as speed indicator
                speed = np.linalg.norm(rotvec)
                raw_speeds.append(speed)
            else:
                raw_speeds.append(0.0)
                
            prev_quat = quat
        
        # Apply moving average filter to reduce noise (smoothing window of 5 samples)
        smoothed_speeds = np.convolve(raw_speeds, np.ones(5)/5, mode='same')
        
        # Apply speed threshold - ignore very small rotations (noise floor)
        speed_threshold = np.percentile(smoothed_speeds, 25)  # Bottom 25% treated as noise
        
        # Rebuild positions with smoothed data
        position = np.array([0.0, 0.0, 0.0])
        for i, point in enumerate(self.data):
            quat = np.array([point['q0'], point['q1'], point['q2'], point['q3']])
            r_curr = R.from_quat([quat[1], quat[2], quat[3], quat[0]])
            
            speed = smoothed_speeds[i]
            
            # Only move if speed exceeds noise threshold
            if speed > speed_threshold:
                # Determine forward direction based on coordinate system
                if self.coordinate_system == 'ground':
                    # Ground frame: X=left/right (target line), Y=up/down, Z=in/out from golfer
                    # At address: Cal Z (face normal) points along target line (User X)
                    # Use face normal as forward direction along X-axis
                    face_direction = r_curr.apply([0, 0, 1])  # Cal Z = face normal
                    # Project to user coordinate frame: face_direction becomes X-movement
                    forward = np.array([face_direction[2], face_direction[0], face_direction[1]])
                else:
                    # Club frame: X=up shaft, Y=toe-heel, Z=face normal
                    forward = r_curr.apply([1, 0, 0])  # Use shaft direction as forward
                    
                position = position + forward * speed * 0.05  # Reduced scale factor (was 0.1)
            
            self.velocities.append(speed)
            self.positions.append(position.copy())
            
        self.positions = np.array(self.positions)
        self.velocities = np.array(self.velocities)
        
    def show(self):
        """Display the 3D visualization"""
        # Create maximized figure
        fig = plt.figure()
        fig.canvas.manager.window.state('zoomed')  # Maximize window
        
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
            r = R.from_quat([quat[1], quat[2], quat[3], quat[0]])
            forward = r.apply([0, 0, 0.15])
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
        r = R.from_rotvec(angle * axis)
        quat = r.as_quat()  # [x, y, z, w]
        
        test_data.append({
            'q0': quat[3],  # w
            'q1': quat[0],  # x
            'q2': quat[1],  # y
            'q3': quat[2],  # z
            'timestamp': i * 0.02
        })
    
    visualizer = SwingVisualizer(test_data)
    visualizer.show()
