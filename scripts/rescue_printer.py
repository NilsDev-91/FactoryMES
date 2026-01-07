import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker
from app.models.core import Printer, PrinterStatusEnum
from sqlmodel import select

async def rescue():
    print("🆘 Rescuing Printer State...")
    async with async_session_maker() as session:
        stmt = select(Printer)
        res = await session.exec(stmt)
        printers = res.all()
        
        for p in printers:
            print(f"   - Updating {p.name} ({p.serial}): {p.current_status} -> IDLE")
            p.current_status = PrinterStatusEnum.IDLE
            p.is_plate_cleared = True
            p.current_job_id = None
            session.add(p)
        
        await session.commit()
    print("✅ Rescue complete. Automation should now be able to pick up jobs.")

if __name__ == "__main__":
    asyncio.run(rescue())
