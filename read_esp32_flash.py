"""
Read flash memory from ESP32 device
This script will dump the flash contents to a binary file
"""
import subprocess
import sys

PORT = "COM11"
OUTPUT_FILE = "esp32_flash_dump.bin"
FLASH_SIZE = "8MB"  # XIAO ESP32-S3 has 8MB flash

def read_flash():
    """Read the entire flash memory from ESP32"""
    print(f"Reading flash from {PORT}...")
    print(f"This will take a few minutes for {FLASH_SIZE} flash...")
    
    # Use esptool to read flash
    # For XIAO ESP32-S3: 8MB = 0x800000 bytes
    cmd = [
        "python", "-m", "esptool",
        "--port", PORT,
        "--baud", "921600",  # Faster baud rate for reading
        "read_flash",
        "0x0",  # Start address
        "0x800000",  # 8MB in hex
        OUTPUT_FILE
    ]
    
    print(f"Command: {' '.join(cmd)}")
    print("\nReading flash memory...")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        if result.returncode == 0:
            print(f"\n✓ Flash successfully saved to: {OUTPUT_FILE}")
            print(f"\nTo analyze the firmware:")
            print(f"  1. Use 'esptool.py image_info {OUTPUT_FILE}' to see partition info")
            print(f"  2. Extract app partition and disassemble with xtensa tools")
            print(f"  3. Compare with your compiled binary in .pio/build/seeed_xiao_esp32s3/")
        else:
            print(f"\n✗ Failed to read flash (exit code: {result.returncode})")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        print("\nMake sure esptool is installed: pip install esptool")

def get_chip_info():
    """Get basic chip information"""
    print("Getting chip information...")
    cmd = [
        "python", "-m", "esptool",
        "--port", PORT,
        "chip_id"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("ESP32 Flash Memory Reader")
    print("=" * 60)
    
    # First get chip info
    get_chip_info()
    
    print("\n" + "=" * 60)
    response = input("\nRead entire flash memory? (y/n): ")
    if response.lower() == 'y':
        read_flash()
    else:
        print("Cancelled.")
