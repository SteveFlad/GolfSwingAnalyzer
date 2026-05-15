"""
Real-time Sensor Movement Test - Bluetooth Version
Shows live quaternion data and angular velocity to verify sensor is working
"""
import asyncio
import time
import numpy as np
import sys

try:
    from bleak import BleakClient, BleakScanner
    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False
    print("ERROR: bleak library not installed!")
    print("Install with: pip install bleak")
    sys.exit(1)

# BLE UUIDs matching ESP32 firmware
SERVICE_UUID = "12345678-1234-1234-1234-123456789abc"
CHARACTERISTIC_UUID = "87654321-4321-4321-4321-cba987654321"

async def scan_for_devices():
    """Scan for BLE devices"""
    print("Scanning for BLE devices (10 seconds)...")
    devices = await BleakScanner.discover(timeout=10.0)
    
    esp32_devices = []
    for d in devices:
        if d.name and ('ESP32' in d.name or 'XIAO' in d.name or 'Golf' in d.name):
            esp32_devices.append(d)
    
    return esp32_devices

def parse_quaternion(line):
    """Parse quaternion from BLE data"""
    try:
        parts = line.strip().split()
        if len(parts) >= 4:
            q = {}
            for part in parts:
                if ':' in part:
                    key, value = part.split(':')
                    if key in ['Q0', 'Q1', 'Q2', 'Q3']:
                        q[key.lower()] = float(value)
            if len(q) == 4:
                return np.array([q['q0'], q['q1'], q['q2'], q['q3']])
    except:
        pass
    return None

def calculate_angular_velocity(q_prev, q_curr, dt):
    """Calculate angular velocity in degrees per second"""
    if dt == 0:
        return 0.0
    dot_product = np.dot(q_prev, q_curr)
    angle = 2 * np.arccos(min(abs(dot_product), 1.0))
    return np.degrees(angle) / dt

# Global variables for data tracking
prev_quat = None
prev_time = None
sample_count = 0
max_velocity = 0.0
total_rotation = 0.0

def notification_handler(sender, data):
    """Handle incoming BLE notifications"""
    global prev_quat, prev_time, sample_count, max_velocity, total_rotation
    
    try:
        line = data.decode('utf-8', errors='ignore')
        quat = parse_quaternion(line)
        
        if quat is not None:
            current_time = time.time()
            sample_count += 1
            
            if prev_quat is not None and prev_time is not None:
                dt = current_time - prev_time
                ang_vel = calculate_angular_velocity(prev_quat, quat, dt)
                max_velocity = max(max_velocity, ang_vel)
                
                # Calculate rotation angle
                dot_product = np.dot(prev_quat, quat)
                angle = 2 * np.arccos(min(abs(dot_product), 1.0))
                total_rotation += np.degrees(angle)
                
                # Color coding for velocity
                if ang_vel > 10:
                    vel_str = f"\033[91m{ang_vel:7.2f}\033[0m"  # Red for high velocity
                elif ang_vel > 2:
                    vel_str = f"\033[93m{ang_vel:7.2f}\033[0m"  # Yellow for medium
                else:
                    vel_str = f"{ang_vel:7.2f}"  # Normal for low
                
                print(f"{sample_count:6d} | {quat[0]:7.4f} | {quat[1]:7.4f} | "
                      f"{quat[2]:7.4f} | {quat[3]:7.4f} | {vel_str} | {total_rotation:10.2f}",
                      end='\r')
                sys.stdout.flush()
            else:
                print(f"{sample_count:6d} | {quat[0]:7.4f} | {quat[1]:7.4f} | "
                      f"{quat[2]:7.4f} | {quat[3]:7.4f} | Starting... | {total_rotation:10.2f}",
                      end='\r')
                sys.stdout.flush()
            
            prev_quat = quat
            prev_time = current_time
    except Exception as e:
        pass  # Ignore parsing errors

async def run_test(device_address):
    """Run the sensor test with BLE connection"""
    global sample_count, max_velocity, total_rotation
    
    print(f"\nConnecting to {device_address}...")
    
    try:
        async with BleakClient(device_address, timeout=10.0) as client:
            print("✓ Connected!\n")
            
            print("Sample | Q0      | Q1      | Q2      | Q3      | Ang.Vel (°/s) | Total Rot (°)")
            print("-" * 80)
            
            # Subscribe to notifications
            await client.start_notify(CHARACTERISTIC_UUID, notification_handler)
            
            # Keep connection alive and monitor data
            try:
                while True:
                    await asyncio.sleep(0.1)
            except KeyboardInterrupt:
                print("\n\n" + "=" * 70)
                await client.stop_notify(CHARACTERISTIC_UUID)
                
    except Exception as e:
        print(f"\nERROR: Connection failed: {e}")
        return False
    
    return True

async def main():
    """Main function"""
    print("=" * 70)
    print("SENSOR MOVEMENT TEST - Real-time Quaternion Monitor (Bluetooth)")
    print("=" * 70)
    print("\nThis tool will show live sensor data to verify movement is detected.")
    print("INSTRUCTIONS:")
    print("  1. Keep sensor still for 3 seconds to establish baseline")
    print("  2. Then SLOWLY rotate the sensor in different directions")
    print("  3. Watch for changing quaternion values and angular velocity")
    print("  4. Press Ctrl+C to stop")
    print("\n" + "=" * 70 + "\n")
    
    # Scan for devices
    devices = await scan_for_devices()
    
    if not devices:
        print("\nERROR: No ESP32/Golf Swing devices found!")
        print("Make sure the device is powered on and in range.")
        return
    
    print(f"\nFound {len(devices)} device(s):")
    for i, d in enumerate(devices):
        print(f"  {i+1}. {d.name} ({d.address})")
    
    # Use first device
    selected_device = devices[0]
    print(f"\nUsing: {selected_device.name} ({selected_device.address})")
    
    # Run the test
    try:
        await run_test(selected_device.address)
    except KeyboardInterrupt:
        pass
    finally:
        print("\n" + "=" * 70)
        print("SUMMARY:")
        print(f"  Total samples: {sample_count}")
        print(f"  Max angular velocity: {max_velocity:.2f} °/s")
        print(f"  Total rotation: {total_rotation:.2f} degrees")
        
        if total_rotation < 20:
            print("\n⚠️  WARNING: Very little movement detected!")
            print("   Expected: 100-500+ degrees for a golf swing")
            print("   Check: Is the sensor powered on and properly mounted?")
        elif total_rotation < 100:
            print("\n⚠️  Small movement detected")
            print("   Expected: 100-500+ degrees for a full golf swing")
        else:
            print("\n✓ Good movement detected!")
            print("  This should produce a visible swing visualization")
        print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
