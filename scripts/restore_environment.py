import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker
from sqlmodel import select, delete
from app.models.core import Printer, PrinterStatusEnum, ClearingStrategyEnum
from app.models.filament import AmsSlot

async def restore_environment():
    REAL_SERIAL = "03919C461802608"
    
    print(f"🧹 Restoring environment... Targeting REAL_SERIAL: {REAL_SERIAL}")
    
    async with async_session_maker() as session:
        # 1. Delete all other printers and their AMS slots
        stmt = select(Printer.serial).where(Printer.serial != REAL_SERIAL)
        other_serials = (await session.exec(stmt)).all()
        
        if other_serials:
            print(f"🚮 Deleting mock printers: {other_serials}")
            await session.exec(delete(AmsSlot).where(AmsSlot.printer_id != REAL_SERIAL))
            await session.exec(delete(Printer).where(Printer.serial != REAL_SERIAL))
        
        # 2. Restore/Update the real printer
        stmt_real = select(Printer).where(Printer.serial == REAL_SERIAL)
        real_printer = (await session.exec(stmt_real)).first()
        
        if real_printer:
            print(f"⚙️  Resetting '{REAL_SERIAL}' to 'A1 REAL' configuration...")
            real_printer.name = "A1 REAL"
            real_printer.current_status = PrinterStatusEnum.IDLE
            real_printer.is_plate_cleared = True
            real_printer.can_auto_eject = True
            real_printer.clearing_strategy = ClearingStrategyEnum.A1_GANTRY_SWEEP
            session.add(real_printer)
        else:
            print(f"⚠️  Real printer '{REAL_SERIAL}' not found! Did it get deleted? Re-seeding as A1 REAL...")
            from app.models.core import PrinterTypeEnum
            real_printer = Printer(
                serial=REAL_SERIAL,
                name="A1 REAL",
                type=PrinterTypeEnum.A1,
                current_status=PrinterStatusEnum.IDLE,
                is_plate_cleared=True,
                can_auto_eject=True,
                clearing_strategy=ClearingStrategyEnum.A1_GANTRY_SWEEP
            )
            session.add(real_printer)
            
        await session.commit()
    print("✅ Environment restored. Only 'A1 REAL' remains.")

if __name__ == "__main__":
    asyncio.run(restore_environment())
