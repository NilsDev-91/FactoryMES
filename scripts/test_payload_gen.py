from app.services.logic.filament_manager import FilamentManager
from app.models.core import Printer, Job
from app.models.filament import AmsSlot
import asyncio
from unittest.mock import MagicMock

async def test():
    # Mock Printer with Slots
    p = Printer(serial="TEST_SERIAL", ip_address="127.0.0.1", access_code="1234")
    p.ams_slots = []
    
    # Slot 1 (Index 0): Blue
    p.ams_slots.append(AmsSlot(printer_serial=p.serial, ams_index=0, slot_index=0, tray_color="#0000FF", tray_type="PLA"))
    # Slot 2 (Index 1): Green
    p.ams_slots.append(AmsSlot(printer_serial=p.serial, ams_index=0, slot_index=1, tray_color="#00FF00", tray_type="PLA"))
    # Slot 3 (Index 2): Red
    p.ams_slots.append(AmsSlot(printer_serial=p.serial, ams_index=0, slot_index=2, tray_color="#C12E1F", tray_type="PLA"))
    # Slot 4 (Index 3): White
    p.ams_slots.append(AmsSlot(printer_serial=p.serial, ams_index=0, slot_index=3, tray_color="#FFFFFF", tray_type="PLA"))

    fm = FilamentManager()
    
    # Helper to check requirement
    def check(color_hex, name):
        print(f"\nTesting Requirement: {name} ({color_hex})")
        reqs = [{"material": "PLA", "hex_color": color_hex, "virtual_id": 0}]
        mapping = fm._match_printer(p, reqs)
        print(f"   Calculated Mapping (FilamentManager Return): {mapping}")
        
        if mapping:
            # Simulate Commander Broadcast Logic
            final_payload = mapping * 16 if len(mapping) == 1 else mapping
            print(f"   Final Sent Payload (Commander Logic): {final_payload}")
            return final_payload
        else:
            print("   ❌ No Match Found")
            return None

    # Test White (Should match Slot 4/Index 3 -> Send 4)
    res_white = check("#FFFFFF", "White")
    
    # Test Red (Should match Slot 3/Index 2 -> Send 3)
    res_red = check("#C12E1F", "Red")

    # Verification
    if res_white and res_white[0] == 4:
         print("\n✅ WHITE TEST PASSED: Maps to 4")
    else:
         print(f"\n❌ WHITE TEST FAILED: Expected 4, got {res_white[0] if res_white else 'None'}")

if __name__ == "__main__":
    asyncio.run(test())
