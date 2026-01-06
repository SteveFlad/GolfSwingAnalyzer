"""
ICM-20948 Sensor Calibration Module
Handles calibration of sensor orientation for different mounting positions
"""

import numpy as np
import json
import time
from pathlib import Path


class SensorCalibration:
    """
    Calibrates the ICM-20948 sensor to account for different mounting orientations
    on the golf club head.
    """
    
    def __init__(self, calibration_file='calibration_data.json'):
        self.calibration_file = Path(calibration_file)
        self.rotation_matrix = np.eye(3)  # Identity matrix (no rotation)
        self.axis_signs = np.array([1, 1, 1])  # No sign flips
        self.gravity_reference = np.array([0, 0, 9.81])  # Expected gravity in club frame
        self.is_calibrated = False
        self.load_calibration()
    
    def load_calibration(self):
        """Load calibration from file if it exists"""
        if self.calibration_file.exists():
            try:
                with open(self.calibration_file, 'r') as f:
                    data = json.load(f)
                    self.rotation_matrix = np.array(data['rotation_matrix'])
                    self.axis_signs = np.array(data['axis_signs'])
                    self.gravity_reference = np.array(data['gravity_reference'])
                    self.is_calibrated = data.get('is_calibrated', False)
                    print(f"Loaded calibration from {self.calibration_file}")
                    return True
            except Exception as e:
                print(f"Failed to load calibration: {e}")
        return False
    
    def save_calibration(self):
        """Save calibration to file"""
        try:
            data = {
                'rotation_matrix': self.rotation_matrix.tolist(),
                'axis_signs': self.axis_signs.tolist(),
                'gravity_reference': self.gravity_reference.tolist(),
                'is_calibrated': self.is_calibrated,
                'timestamp': time.time()
            }
            with open(self.calibration_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"Calibration saved to {self.calibration_file}")
            return True
        except Exception as e:
            print(f"Failed to save calibration: {e}")
            return False
    
    def calibrate_from_positions(self, position_samples):
        """
        Calibrate sensor from multiple position samples
        
        Parameters:
        -----------
        position_samples : dict
            Dictionary with keys: 'address', 'toe_up', 'toe_down', 'face_up'
            Each position contains lists of accelerometer readings [ax, ay, az]
        
        Returns:
        --------
        bool: True if calibration successful
        """
        try:
            # Extract average values for each position
            address_data = np.array(position_samples['address'])
            toe_up_data = np.array(position_samples['toe_up'])
            toe_down_data = np.array(position_samples['toe_down'])
            face_up_data = np.array(position_samples['face_up'])
            
            # Calculate mean acceleration for each position
            address_mean = np.mean(address_data, axis=0)
            toe_up_mean = np.mean(toe_up_data, axis=0)
            toe_down_mean = np.mean(toe_down_data, axis=0)
            face_up_mean = np.mean(face_up_data, axis=0)
            
            # Normalize vectors
            address_norm = address_mean / np.linalg.norm(address_mean)
            toe_up_norm = toe_up_mean / np.linalg.norm(toe_up_mean)
            toe_down_norm = toe_down_mean / np.linalg.norm(toe_down_mean)
            face_up_norm = face_up_mean / np.linalg.norm(face_up_mean)
            
            # Define target axes in club frame:
            # X-axis: Along shaft (toward grip) - address position should be vertical
            # Y-axis: Toe-heel direction (positive toward toe)
            # Z-axis: Face normal (positive toward target)
            
            # Z-axis (down in address position, should align with gravity)
            z_sensor = -address_norm  # Negative because gravity points down
            
            # Y-axis (perpendicular to shaft, toe direction)
            # Toe up should oppose toe down
            y_sensor = (toe_up_norm - toe_down_norm) / 2.0
            y_sensor = y_sensor / np.linalg.norm(y_sensor)
            
            # X-axis (perpendicular to both, should point up shaft toward grip)
            # Use cross product to ensure orthogonal
            x_sensor = np.cross(y_sensor, z_sensor)
            x_sensor = x_sensor / np.linalg.norm(x_sensor)
            
            # Recalculate Y to ensure perfect orthogonality
            y_sensor = np.cross(z_sensor, x_sensor)
            
            # Build rotation matrix (columns are the new basis vectors)
            # This transforms from sensor frame to club frame
            self.rotation_matrix = np.column_stack([x_sensor, y_sensor, z_sensor])
            
            # Verify it's a proper rotation matrix (determinant should be +1)
            det = np.linalg.det(self.rotation_matrix)
            if abs(det - 1.0) > 0.1:
                print(f"Warning: Rotation matrix determinant = {det:.3f} (should be 1.0)")
                return False
            
            # Determine axis signs based on face_up position
            # Face up should give positive Z acceleration in club frame
            face_up_club = self.transform_accel(face_up_mean)
            
            # Store results
            self.is_calibrated = True
            self.save_calibration()
            
            print("Calibration successful!")
            print(f"Rotation matrix:\n{self.rotation_matrix}")
            print(f"Face up validation: {face_up_club}")
            
            return True
            
        except Exception as e:
            print(f"Calibration failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def calibrate_simple(self, gravity_samples):
        """
        Simple calibration using only gravity direction in address position
        
        Parameters:
        -----------
        gravity_samples : list
            List of accelerometer readings [ax, ay, az] when club is at address
        
        Returns:
        --------
        bool: True if calibration successful
        """
        try:
            # Calculate mean gravity vector
            gravity_data = np.array(gravity_samples)
            gravity_sensor = np.mean(gravity_data, axis=0)
            
            # Normalize
            gravity_norm = np.linalg.norm(gravity_sensor)
            if gravity_norm < 8.0 or gravity_norm > 12.0:
                print(f"Warning: Gravity magnitude = {gravity_norm:.2f} m/s² (expected ~9.8)")
            
            gravity_unit = gravity_sensor / gravity_norm
            
            # Find which sensor axis is most aligned with gravity
            abs_components = np.abs(gravity_unit)
            primary_axis = np.argmax(abs_components)
            
            # Determine sign (gravity points down, so we need negative)
            primary_sign = -np.sign(gravity_unit[primary_axis])
            
            # Build simple transformation (swap axes if needed)
            # Map the primary axis to Z (down in address)
            self.axis_signs = np.ones(3)
            self.axis_signs[primary_axis] = primary_sign
            
            # Store simple rotation that swaps axes
            if primary_axis == 0:
                # X is vertical -> swap X and Z
                self.rotation_matrix = np.array([
                    [0, 0, 1],
                    [0, 1, 0],
                    [1, 0, 0]
                ])
            elif primary_axis == 1:
                # Y is vertical -> swap Y and Z
                self.rotation_matrix = np.array([
                    [1, 0, 0],
                    [0, 0, 1],
                    [0, 1, 0]
                ])
            else:
                # Z is vertical -> no swap needed
                self.rotation_matrix = np.eye(3)
            
            self.is_calibrated = True
            self.save_calibration()
            
            print("Simple calibration successful!")
            print(f"Primary axis: {['X', 'Y', 'Z'][primary_axis]} (sign: {primary_sign})")
            print(f"Gravity in sensor frame: {gravity_sensor}")
            
            return True
            
        except Exception as e:
            print(f"Simple calibration failed: {e}")
            return False
    
    def transform_accel(self, accel_sensor):
        """
        Transform accelerometer reading from sensor frame to club frame
        
        Parameters:
        -----------
        accel_sensor : array-like
            Accelerometer reading in sensor frame [ax, ay, az]
        
        Returns:
        --------
        np.ndarray: Accelerometer reading in club frame
        """
        accel = np.array(accel_sensor)
        
        # Apply axis signs
        accel = accel * self.axis_signs
        
        # Apply rotation
        accel_club = self.rotation_matrix.T @ accel
        
        return accel_club
    
    def transform_gyro(self, gyro_sensor):
        """
        Transform gyroscope reading from sensor frame to club frame
        
        Parameters:
        -----------
        gyro_sensor : array-like
            Gyroscope reading in sensor frame [gx, gy, gz]
        
        Returns:
        --------
        np.ndarray: Gyroscope reading in club frame
        """
        gyro = np.array(gyro_sensor)
        
        # Apply axis signs
        gyro = gyro * self.axis_signs
        
        # Apply rotation
        gyro_club = self.rotation_matrix.T @ gyro
        
        return gyro_club
    
    def transform_quaternion(self, quat_sensor):
        """
        Transform quaternion from sensor frame to club frame
        
        Parameters:
        -----------
        quat_sensor : array-like
            Quaternion in sensor frame [w, x, y, z]
        
        Returns:
        --------
        np.ndarray: Quaternion in club frame
        """
        # For proper quaternion transformation, we'd need to:
        # 1. Convert quaternion to rotation matrix
        # 2. Apply calibration rotation
        # 3. Convert back to quaternion
        # For now, return as-is (this is a simplification)
        return np.array(quat_sensor)
    
    def get_calibration_status(self):
        """Return calibration status as string"""
        if self.is_calibrated:
            return "Calibrated"
        else:
            return "Not Calibrated"
    
    def reset_calibration(self):
        """Reset calibration to identity"""
        self.rotation_matrix = np.eye(3)
        self.axis_signs = np.array([1, 1, 1])
        self.is_calibrated = False
        if self.calibration_file.exists():
            self.calibration_file.unlink()
        print("Calibration reset")
