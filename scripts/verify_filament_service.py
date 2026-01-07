
import asyncio
import sys
import os
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Setup path
sys.path.append(os.getcwd())

from app.services.filament_service import FilamentService
from app.models.filament import AmsSlot
from app.models.core import Printer, PrinterTypeEnum
from app.core.database import async_session_maker

async def verify_filament_service():
    print("🧪 Verifying FilamentService...")
    
    async with async_session_maker() as session:
        service = FilamentService(session)
        
        # 1. Delta E Test
        print("\n1. Testing Delta E calculation...")
        white = "#FFFFFF"
        black = "#000000"
        red = "#FF0000"
        light_red = "#FF3333"
        
        de_wb = service.calculate_delta_e(white, black)
        de_rr = service.calculate_delta_e(red, light_red)
        
        print(f"   - White vs Black Delta E: {de_wb:.2f} (Expected: High)")
        print(f"   - Red vs Light Red Delta E: {de_rr:.2f} (Expected: Low)")
        
        # In LAB/Delta E 2000, White vs Black is around 100
        assert de_wb > 50
        assert de_rr < 15

        # 2. Match Test (Mock data)
        print("\n2. Testing Best Match Engine...")
        
        # Setup mock printer and slots
        serial = "TEST_SERIAL_FMS_VERIFY"
        existing_printer = await session.get(Printer, serial)
        if not existing_printer:
            printer = Printer(
                serial=serial,
                name="Test Printer",
                type=PrinterTypeEnum.A1
            )
            session.add(printer)
            await session.flush()
        
        # Add some slots
        slots = [
            AmsSlot(printer_id=serial, ams_index=0, slot_index=0, slot_id=0, color_hex="#FF0000", material="PLA", remaining_percent=50),
            AmsSlot(printer_id=serial, ams_index=0, slot_index=1, slot_id=1, color_hex="#00FF00", material="PLA", remaining_percent=50),
            AmsSlot(printer_id=serial, ams_index=0, slot_index=2, slot_id=2, color_hex="#0000FF", material="PETG", remaining_percent=50),
        ]
        
        for s in slots:
            stmt = select(AmsSlot).where(AmsSlot.printer_id == serial, AmsSlot.ams_index == s.ams_index, AmsSlot.slot_index == s.slot_index)
            res = await session.execute(stmt)
            if not res.scalars().first():
                session.add(s)
        
        await session.flush()
        
        # Test finding match
        match = await service.find_best_match_for_job("#EE0000", "PLA", printer_id=serial)
        if match:
            print(f"   - Match found: {match.color_hex} on slot {match.slot_id} (Expected: #FF0000)")
            assert match.color_hex == "#FF0000"
        else:
            print("   - ❌ Failed: No match found for #EE0000")
            
        # 3. Payload Sync Test
        print("\n3. Testing AMS Payload Sync...")
        ams_payload = {
            "ams": [
                {
                    "id": "0",
                    "tray": [
                        {"id": "0", "tray_color": "000000FF", "tray_type": "PLA", "remain": "80"},
                        {"id": "1", "tray_color": "FFFFFF", "tray_type": "PLA", "remain": "10"}
                    ]
                }
            ]
        }
        
        await service.sync_ams_configuration(serial, ams_payload)
        await session.commit()
        
        # Verify sync
        stmt = select(AmsSlot).where(AmsSlot.printer_id == serial, AmsSlot.slot_index == 0)
        res = await session.execute(stmt)
        updated_slot = res.scalars().first()
        
        if updated_slot:
            print(f"   - Synced Slot 0 Color: {updated_slot.color_hex} (Expected: 000000FF)")
            print(f"   - Resolved Color Name: {updated_slot.color_name} (Expected: Black)")
            assert updated_slot.color_hex == "000000FF"
            assert updated_slot.color_name == "Black"
        else:
            print("   - ❌ Failed: Slot 0 not synced correctly")

    print("\n✅ Verification Complete!")

if __name__ == "__main__":
    asyncio.run(verify_filament_service())
