from app.services.printer.kinematics import A1Kinematics, KinematicSafetyError
from app.schemas.job import PartMetadata
import logging

# Setup minimal logging
logging.basicConfig(level=logging.INFO)

def test_kinematics():
    test_cases = [
        {"height": 120.0, "expected_z": 82.0, "desc": "Zylinder V2 (Master)"},
        {"height": 40.0,  "expected_z": 2.0,  "desc": "Threshold Case (40mm)"},
        {"height": 50.0,  "expected_z": 12.0, "desc": "Standard Case (50mm)"},
        {"height": 35.0,  "should_fail": True, "desc": "Unsafe Height (35mm)"},
    ]

    print("\n--- A1 Kinematics Verification ---")
    
    for case in test_cases:
        height = case["height"]
        desc = case["desc"]
        print(f"\nTesting: {desc} ({height}mm)")
        
        meta = PartMetadata(height_mm=height)
        
        try:
            # 1. Test calculation directly
            calc_z = A1Kinematics._calculate_sweep_z(height)
            print(f"  Calculation: {calc_z}mm")
            
            if case.get("should_fail"):
                print(f"  FAILED: Should have raised KinematicSafetyError for {height}mm")
                continue
                
            if calc_z != case["expected_z"]:
                print(f"  FAILED: Expected {case['expected_z']}mm, got {calc_z}mm")
            else:
                print("  Calculation Verification: PASSED")

            # 2. Test G-code Generation
            gcode = A1Kinematics.generate_a1_gantry_sweep_gcode(meta)
            z_line = f"G1 Z{calc_z:.1f}"
            if z_line in gcode:
                print(f"  G-code Injection: PASSED ({z_line})")
            else:
                print(f"  FAILED: Could not find '{z_line}' in G-code")
                # print(gcode)

        except KinematicSafetyError as e:
            if case.get("should_fail"):
                print(f"  Safety Guard Verification: PASSED ({e})")
            else:
                print(f"  FAILED: Unexpected KinematicSafetyError: {e}")
        except Exception as e:
            print(f"  CRITICAL ERROR: {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_kinematics()
