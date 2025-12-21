# PyBluez Installation Issues & Workarounds

## The Problem

PyBluez 0.23 (the latest version on PyPI) uses the deprecated `use_2to3` setuptools feature, which was removed in setuptools 58.0+. This causes installation to fail on modern Python environments.

## Solutions

### Option 1: Use USB/Serial Connection (Recommended)

The simplest solution is to use the USB/Serial connection instead of Bluetooth:
- More reliable
- Lower latency
- No installation issues
- Works on all platforms

The application will work perfectly without Bluetooth support.

### Option 2: Install PyBluez from Source (Advanced)

Install a patched version from the fork:

```bash
pip install git+https://github.com/pybluez/pybluez.git#egg=pybluez
```

**Windows Requirements:**
- Visual Studio Build Tools
- Windows SDK
- May require admin privileges

### Option 3: Downgrade setuptools (Not Recommended)

```bash
pip install setuptools==57.5.0
pip install pybluez
pip install --upgrade setuptools
```

This is a temporary workaround and may cause other compatibility issues.

### Option 4: Use Alternative Libraries (Future)

For Bluetooth Low Energy (BLE), consider using:

```bash
pip install bleak
```

**Note:** The current Golf Swing Analyzer uses Bluetooth Classic (SPP), not BLE. Using `bleak` would require firmware and software modifications.

## Platform-Specific Notes

### Windows
- PyBluez requires Microsoft Visual C++ 14.0 or greater
- Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
- Install "Desktop development with C++" workload
- May need to run as Administrator

### Linux (Ubuntu/Debian)
```bash
sudo apt-get install bluetooth libbluetooth-dev
pip install git+https://github.com/pybluez/pybluez.git#egg=pybluez
```

### macOS
PyBluez has limited support on macOS. Consider:
- Using USB/Serial connection
- Using alternative BLE libraries like `bleak`

## Recommendation

**For most users**: Use the USB/Serial connection. It's simpler, more reliable, and doesn't require additional setup.

**For wireless operation**: Consider these alternatives:
1. Use a longer USB cable
2. Wait for better Bluetooth library support
3. Use WiFi (could be implemented as an alternative)

## Checking Installation Status

The Golf Swing Analyzer will automatically detect if Bluetooth support is available:
- If PyBluez is not installed, the Bluetooth option will be disabled (grayed out)
- The application will show a message: "Note: Bluetooth support not available"
- All other features will work normally via USB/Serial

## Future Plans

We're considering:
- Implementing WiFi support (more reliable than Bluetooth)
- Supporting BLE with the `bleak` library
- Creating pre-compiled binaries with Bluetooth support included

For now, USB/Serial is the recommended connection method.
