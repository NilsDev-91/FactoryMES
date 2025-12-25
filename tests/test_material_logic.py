
import json
import logging
from typing import List, Dict, Union, Optional

# --- Mocking Data Classes based on Prompt ---

class Printer:
    def __init__(self, name, ams_data):
        self.name = name
        self.ams_data = ams_data

class Product:
    def __init__(self, name, required_filament_type, required_filament_color=None):
        self.name = name
        self.required_filament_type = required_filament_type
        self.required_filament_color = required_filament_color

# --- The Logic under test ---

logger = logging.getLogger("Test")
logging.basicConfig(level=logging.INFO)

def check_material_match(printer: Printer, product: Product) -> bool:
    """
    Checks if the printer has the required filament loaded in AMS.
    Returns True if match found or if product has no specific requirements.
    """
    req_type = product.required_filament_type
    req_color = product.required_filament_color

    if not req_type:
        return True

    if not printer.ams_data:
        # Fallback: If no AMS data available, assume NO match to be safe.
        # logger.debug(f"Printer {printer.name} has no AMS data.")
        return False

    # Parse AMS data
    if isinstance(printer.ams_data, str):
         ams_slots = json.loads(printer.ams_data)
    else:
         ams_slots = printer.ams_data

    for slot in ams_slots:
        slot_type = slot.get('type', 'UNKNOWN')
        slot_color = slot.get('color', '')

        # Type Check (Case insensitive)
        type_match = req_type.lower() in slot_type.lower()
        
        # Color Check (only if product requires color)
        color_match = True
        if req_color:
            # Simple string check for now
            color_match = req_color.lower() == slot_color.lower()

        if type_match and color_match:
            # logger.info(f"Material Match! Printer {printer.name} Slot {slot.get('slot')} has {slot_type} {slot_color}")
            return True

    return False

# --- Test Cases ---

def run_tests():
    print("Running Logic Verification Tests...\n")

    # 1. Substring Match Risk
    p1 = Printer("P1", ams_data=[
        {"slot": 0, "type": "Support for PLA", "color": "#FFFFFF", "remaining": 100}
    ])
    prod1 = Product("PLA Model", "PLA")
    
    match1 = check_material_match(p1, prod1)
    print(f"Test 1: 'PLA' matching 'Support for PLA': {match1} (Expected: False/Risk?) -> {'RISK' if match1 else 'SAFE'}")

    # 2. Empty Spool Risk (Assuming logic doesn't check remaining)
    p2 = Printer("P2", ams_data=[
        {"slot": 0, "type": "PLA", "color": "#FF0000", "remaining": 0}
    ])
    prod2 = Product("Red PLA Model", "PLA", "#FF0000")
    
    match2 = check_material_match(p2, prod2)
    print(f"Test 2: Matching empty spool (remaining=0): {match2} (Expected: False) -> {'FAIL' if match2 else 'PASS'}")

    # 3. Exact Color Match Logic
    p3 = Printer("P3", ams_data=[
        {"slot": 0, "type": "PLA", "color": "Red", "remaining": 100}
    ])
    prod3 = Product("Red Hex Model", "PLA", "#FF0000")
    
    match3 = check_material_match(p3, prod3)
    print(f"Test 3: Color Name vs Hex ('Red' == '#FF0000'): {match3} (Expected: False per current logic) -> {'OK' if not match3 else 'Magical Match'}")

    # 4. Case Insensitivity
    p4 = Printer("P4", ams_data=[
        {"slot": 0, "type": "pla", "color": "#ff0000", "remaining": 100}
    ])
    prod4 = Product("Caps Model", "PLA", "#FF0000")
    match4 = check_material_match(p4, prod4)
    print(f"Test 4: Case Insensitivity: {match4} (Expected: True) -> {'PASS' if match4 else 'FAIL'}")

    # 5. Type Match Safety
    p5 = Printer("P5", ams_data=[
        {"slot": 0, "type": "PLA-CF", "color": "#000000", "remaining": 100}
    ])
    prod5 = Product("PLA Model", "PLA")
    match5 = check_material_match(p5, prod5)
    print(f"Test 5: 'PLA' matches 'PLA-CF': {match5} (Expected: True/Debatable) -> {'MATCH' if match5 else 'NO MATCH'}")

if __name__ == "__main__":
    run_tests()
