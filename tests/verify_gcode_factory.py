from app.models.core import Printer, PrinterTypeEnum
from app.services.production.bed_clearing_service import BedClearingService

def test_a1_factory():
    print("\nTEST: A1 Strategy Generation")
    service = BedClearingService()
    printer = Printer(serial="A1_TEST", type=PrinterTypeEnum.A1, current_status="IDLE")
    
    gcode = service.generate_clearing_gcode(printer)
    print("--- GENERATED GCODE (A1) ---")
    print(gcode)
    print("----------------------------")
    
    assert "M620 S255" in gcode
    assert "M621 S1" in gcode
    assert "M109 S0" in gcode # Safety Guard
    print("PASS: A1 contains expected commands.")

def test_x1_factory():
    print("\nTEST: X1 Ramming Strategy Generation")
    service = BedClearingService()
    printer = Printer(serial="X1_TEST", type=PrinterTypeEnum.X1C, current_status="IDLE")
    
    gcode = service.generate_clearing_gcode(printer)
    print("--- GENERATED GCODE (X1) ---")
    print(gcode)
    print("----------------------------")
    
    assert "M106 P2 S255" in gcode
    assert "G28" in gcode
    assert "G1 X128 Y250" in gcode
    assert "M109 S0" in gcode # Safety Guard
    print("PASS: X1 contains expected commands.")

def test_fallback_factory():
    print("\nTEST: Fallback Strategy")
    # Using a hypothetical type or relying on default mapping if enum was expandable... 
    # But enum is strict. Let's test P1S which maps to X1 strategy.
    
    service = BedClearingService()
    printer = Printer(serial="P1S_TEST", type=PrinterTypeEnum.P1S, current_status="IDLE")
    
    gcode = service.generate_clearing_gcode(printer)
    assert "STRATEGY: X1 MECHANICAL SWEEP" in gcode
    print("PASS: P1S maps to X1 Strategy.")

if __name__ == "__main__":
    test_a1_factory()
    test_x1_factory()
    test_fallback_factory()
    print("\nALL FACTORY TESTS PASSED")
