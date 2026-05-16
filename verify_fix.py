"""
Verify that the capture fix is present in main.py
"""

with open('main.py', 'r') as f:
    content = f.read()

# Check for the fix
if 'self.current_data.append(data_dict.copy())' in content:
    print("✓ FIX PRESENT: Code has .copy() to prevent reference bug")
else:
    print("✗ FIX MISSING: Code still has the bug!")
    
# Check that it's in the right place (before deadband filter)
lines = content.split('\n')
copy_line = None
deadband_line = None

for i, line in enumerate(lines):
    if 'self.current_data.append(data_dict.copy())' in line:
        copy_line = i
    if 'Apply live quaternion deadband filtering' in line:
        deadband_line = i

if copy_line and deadband_line:
    if copy_line < deadband_line:
        print(f"✓ FIX ORDERING CORRECT: Capture (line {copy_line}) happens BEFORE filter (line {deadband_line})")
    else:
        print(f"✗ FIX ORDERING WRONG: Filter happens before capture!")
        
print("\n" + "="*70)
print("TO FIX THE PROBLEM:")
print("1. CLOSE the main.py application if it's running")
print("2. Run: python main.py")
print("3. Connect to sensor")
print("4. Capture a NEW swing")
print("5. Visualize - should show full swing path")
print("="*70)
