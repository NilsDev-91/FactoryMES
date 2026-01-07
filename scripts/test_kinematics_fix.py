import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

from app.services.printer.kinematics import A1Kinematics
from app.services.logic.gcode_modifier import GCodeModifier

def test_kinematics_fix():
    print("--- Testing A1Kinematics Fix (Reverse Ram Bug) ---")
    
    # Test Gantry Sweep (Height > 50mm)
    height_mm = 60.0
    gcode = A1Kinematics.generate_sweep_sequence(height_mm)
    
    print(f"Generated G-Code for {height_mm}mm part:")
    print(gcode)
    
    # Assert Setup matches Y256
    setup_idx = gcode.find("G1 Y256")
    action_idx = gcode.find("G1 Y0")
    
    assert setup_idx != -1, "Missing Setup Move (Y256)"
    assert action_idx != -1, "Missing Action Move (Y0)"
    assert setup_idx < action_idx, "CRITICAL FAIL: Action (Y0) happens before Setup (Y256) - REVERSE RAM BUG!"
    
    print("✅ SEQUENCING PASS: Setup (Y256) occurs before Action (Y0)")
    
    # Assert Z height logic
    # Target Beam Z = 60 * 0.6 = 36mm
    # Nozzle Z = 36 - 33 = 3mm
    assert "Z3.00" in gcode, f"Incorrect Z height calculation. Expected Z3.00, got: {gcode}"
    print("✅ Z-CALC PASS: Correct Z height calculated")

    print("\n--- Testing GCodeModifier Integration ---")
    modifier = GCodeModifier()
    base_gcode = "M104 S0"
    modified = modifier.inject_sweep_sequence(base_gcode, "Bambu Lab A1", height_mm)
    
    assert "FACTORYOS A1 KINEMATICS: GANTRY SWEEP" in modified, "GCodeModifier failed to delegate to A1Kinematics"
    print("✅ DELEGATION PASS: GCodeModifier uses A1Kinematics")

if __name__ == "__main__":
    try:
        test_kinematics_fix()
        print("\n🎉 ALL CHECKS PASSED")
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
