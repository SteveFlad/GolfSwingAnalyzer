"""
Physical Button Trigger for Golf Swing Analyzer
Simpler and more reliable than Bluetooth remote
"""

class ButtonTrigger:
    """Detects physical button trigger from ESP32"""
    
    def __init__(self, callback=None):
        self.callback = callback
        
    def check_serial_data(self, line):
        """
        Call this from your serial monitoring loop
        
        Args:
            line: String from serial port
            
        Returns:
            True if trigger detected
        """
        if "TRIGGER:" in line:
            trigger_type = line.split("TRIGGER:")[1].strip()
            
            if trigger_type == "PRESSED":
                print("🔘 Button trigger: Starting capture...")
                if self.callback:
                    self.callback("start")
                return True
                
        return False

# Integration example for main.py:
"""
# In serial monitor loop, add:

if self.button_trigger:
    if self.button_trigger.check_serial_data(line):
        if not self.monitoring:
            self.start_recording()
"""
