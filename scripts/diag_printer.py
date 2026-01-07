import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker
from sqlmodel import select
from app.models.core import Printer, Job, JobStatusEnum
from app.models.filament import AmsSlot

async def diagnostic():
    async with async_session_maker() as session:
        printer_stmt = select(Printer)
        printers = (await session.exec(printer_stmt)).all()
        for p in printers:
            print(f"PRINTER: {p.serial} | NAME: {p.name} | STATUS: {p.current_status} | CLEARED: {p.is_plate_cleared}")
            ams_stmt = select(AmsSlot).where(AmsSlot.printer_id == p.serial)
            slots = (await session.exec(ams_stmt)).all()
            for s in slots:
                print(f"  SLOT {s.slot_id}: Material={s.material}, Color={s.color_hex}, Name={s.color_name}")
        
        job_stmt = select(Job).where(Job.status == JobStatusEnum.PENDING)
        jobs = (await session.exec(job_stmt)).all()
        for j in jobs:
            print(f"PENDING JOB {j.id}: Reqs={j.filament_requirements}")

if __name__ == "__main__":
    asyncio.run(diagnostic())
