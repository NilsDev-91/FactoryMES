import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

from app.services.logic.gcode_modifier import GCodeModifier

def test_sweep_injection():
    modifier = GCodeModifier()
    sample_gcode = "G1 X10 Y10 ; sample print\nM104 S0 ; end"
    
    print("--- Testing A1 Series Injection ---")
    a1_result = modifier.inject_sweep_sequence(sample_gcode, "Bambu Lab A1", 55.0)
    print(a1_result)
    assert "; Strategy: Gantry Sweep" in a1_result
    assert "G1 Y0 F2000" in a1_result
    
    print("\n--- Testing X1 Series Injection ---")
    x1_result = modifier.inject_sweep_sequence(sample_gcode, "Bambu Lab X1C", 38.0)
    print(x1_result)
    assert "; Strategy: Present Print" in x1_result
    
    print("\nVerification Successful!")

if __name__ == "__main__":
    test_sweep_injection()
