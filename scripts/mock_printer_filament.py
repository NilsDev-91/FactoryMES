import asyncio
from sqlmodel import select
from app.core.database import async_session_maker
from app.models.core import Printer, PrinterStatusEnum
from app.models.filament import AmsSlot

async def mock_printer_filament():
    print("🎨 Mocking Printer Filament...")
    printer_serial = "03919C461802608"

    async with async_session_maker() as session:
        # 1. Get Printer
        printer = await session.get(Printer, printer_serial)
        if not printer:
            print(f"❌ Printer {printer_serial} not found!")
            return

        print(f"✅ Found Printer: {printer.name}")

        # 2. Clear existing slots
        print("   Clearing existing slots...")
        stmt = select(AmsSlot).where(AmsSlot.printer_id == printer_serial)
        existing = await session.exec(stmt)
        for slot in existing.all():
            await session.delete(slot)
        
        # 3. Add White PLA
        print("   Adding White PLA to AMS 0, Slot 0...")
        new_slot = AmsSlot(
            printer_id=printer_serial,
            ams_index=0,
            slot_index=0,
            tray_type="PLA",
            tray_color="#FFFFFF", # White
            remaining_percent=100
        )
        session.add(new_slot)

        # 4. Ensure Printer is IDLE
        print("   Ensuring Printer is IDLE...")
        printer.current_status = PrinterStatusEnum.IDLE
        session.add(printer)

        await session.commit()
        print("✅ Printer mocked successfully. Dispatcher should match it now.")

if __name__ == "__main__":
    asyncio.run(mock_printer_filament())
