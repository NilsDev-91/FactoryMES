import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import async_session_maker, engine
from app.models.core import Printer, PrinterStatusEnum, SQLModel
from app.models.filament import AmsSlot
from sqlmodel import select, text

async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async def test_fms_logic():
    print("Testing FMS Aggregation Logic...")
    
    # 1. Setup Test Data
    test_serial_1 = "FMS_TEST_1"
    test_serial_2 = "FMS_TEST_2"
    
    async with async_session_maker() as session:
        # Cleanup
        await session.exec(text(f"DELETE FROM ams_slots WHERE printer_id IN ('{test_serial_1}', '{test_serial_2}')"))
        await session.exec(text(f"DELETE FROM printers WHERE serial IN ('{test_serial_1}', '{test_serial_2}')"))
        await session.commit()
        
        # Create Printers
        p1 = Printer(serial=test_serial_1, name="FMS P1", type="P1S")
        p2 = Printer(serial=test_serial_2, name="FMS P2", type="P1S")
        session.add(p1)
        session.add(p2)
        await session.commit()
        
        # Create Slots
        # P1: PLA/Red, PLA/Red (Duplicate color on same printer)
        s1 = AmsSlot(printer_id=test_serial_1, ams_index=0, slot_index=0, tray_type="PLA", tray_color="FF0000")
        s2 = AmsSlot(printer_id=test_serial_1, ams_index=0, slot_index=1, tray_type="PLA", tray_color="FF0000")
        # P2: PLA/Red (Duplicate color across printers), PETG/Black
        s3 = AmsSlot(printer_id=test_serial_2, ams_index=0, slot_index=0, tray_type="PLA", tray_color="FF0000")
        s4 = AmsSlot(printer_id=test_serial_2, ams_index=0, slot_index=1, tray_type="PETG", tray_color="000000")
        
        session.add_all([s1, s2, s3, s4])
        await session.commit()
        
    print("✅ Test data created.")

    # 2. Simulate Endpoint Logic
    # We copy the exact logic from the router to verify it works detached from FastAPI context
    
    async with async_session_maker() as session:
        statement = select(AmsSlot)
        result = await session.exec(statement)
        all_slots = result.all() # In production this would fetch ALL, might need filter
        
        aggregator = {}
        for slot in all_slots:
            if not slot.tray_type or not slot.tray_color:
                continue
             # Filter only our test printers to keep it clean
            if slot.printer_id not in [test_serial_1, test_serial_2]:
                continue

            key = (slot.tray_type, slot.tray_color)
            if key not in aggregator:
                aggregator[key] = {"slots": []}
            slot_id = f"{slot.printer_id}/AMS{slot.ams_index}/Slot{slot.slot_index}"
            aggregator[key]["slots"].append(slot_id)
            
    # 3. Verify Results
    print("\nResults:")
    for k, v in aggregator.items():
        print(f"Material: {k[0]}, Color: {k[1]}, Count: {len(v['slots'])}")
        
    # Expect: 
    # ('PLA', 'FF0000') -> 3 slots
    # ('PETG', '000000') -> 1 slot
    
    red_pla = aggregator.get(("PLA", "FF0000"))
    black_petg = aggregator.get(("PETG", "000000"))
    
    if red_pla and len(red_pla['slots']) == 3:
        print("✅ Correctly aggregated 3 PLA Red slots.")
    else:
        print(f"❌ Failed aggregating PLA Red. Got: {red_pla}")
        
    if black_petg and len(black_petg['slots']) == 1:
        print("✅ Correctly identified 1 PETG Black slot.")
    else:
        print(f"❌ Failed identifying PETG Black. Got: {black_petg}")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_fms_logic())
