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
    def __init__(self, data):
        """
        Initialize visualizer with quaternion data
        data: list of dictionaries with keys 'q0', 'q1', 'q2', 'q3', 'timestamp'
        """
        self.data = data
        self.positions = []
        self.velocities = []
        self.orientations = []
        
        self.process_data()
        
    def process_data(self):
        """Convert quaternion data to positions and velocities"""
        # Simulate position by integrating orientation changes
        # In a real application, you might use double integration of accelerometer data
        
        position = np.array([0.0, 0.0, 0.0])
        prev_quat = None
        
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
                
                # Move in the direction indicated by current orientation
                forward = r_curr.apply([0, 0, 1])  # Forward direction
                position = position + forward * speed * 0.1  # Scale factor
                
                self.velocities.append(speed)
            else:
                self.velocities.append(0.0)
                
            self.positions.append(position.copy())
            prev_quat = quat
            
        self.positions = np.array(self.positions)
        self.velocities = np.array(self.velocities)
        
    def show(self):
        """Display the 3D visualization"""
        fig = plt.figure(figsize=(14, 10))
        
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
            s=30,
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
        ax.scatter(*self.positions[0], color='green', s=100, marker='o', label='Start')
        ax.scatter(*self.positions[-1], color='red', s=100, marker='X', label='End')
        
        # Add orientation indicators at key points
        step = max(1, len(self.positions) // 20)
        for i in range(0, len(self.positions), step):
            quat = self.orientations[i]
            r = R.from_quat([quat[1], quat[2], quat[3], quat[0]])
            
            # Face direction (forward vector)
            forward = r.apply([0, 0, 0.5])
            pos = self.positions[i]
            
            ax.quiver(
                pos[0], pos[1], pos[2],
                forward[0], forward[1], forward[2],
                color='red', alpha=0.5, arrow_length_ratio=0.3
            )
        
        ax.set_xlabel('X (m)')
        ax.set_ylabel('Y (m)')
        ax.set_zlabel('Z (m)')
        ax.set_title('3D Club Head Trajectory\n(Red arrows = face direction)')
        ax.legend()
        
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
            forward = r.apply([0, 0, 0.3])
            pos = self.positions[i]
            
            ax.arrow(
                pos[0], pos[1],
                forward[0], forward[1],
                head_width=0.05, head_length=0.05,
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
