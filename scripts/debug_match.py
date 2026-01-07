import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.job_dispatcher import job_dispatcher
from app.core.database import async_session_maker
from sqlmodel import select
from app.models.core import Printer, Job
from sqlalchemy.orm import selectinload

async def debug_dispatch():
    print("🚀 Starting Debug Dispatch...")
    async with async_session_maker() as session:
        # Check Printers
        stmt_prn = select(Printer).options(selectinload(Printer.ams_slots))
        printers = (await session.exec(stmt_prn)).all()
        print(f"Printers found: {len(printers)}")
        for p in printers:
            print(f" - {p.serial} (Status: {p.current_status}, Plate Cleared: {p.is_plate_cleared})")
            print(f"   AMS Slots: {[{'id': s.slot_id, 'mat': s.material, 'col': s.color_hex} for s in p.ams_slots]}")

        # Check Jobs
        stmt_job = select(Job)
        jobs = (await session.exec(stmt_job)).all()
        print(f"Jobs found: {len(jobs)}")
        for j in jobs:
            print(f" - {j.id} (Status: {j.status}, Req: {j.filament_requirements})")
            if j.status == "PENDING" and j.filament_requirements:
                print("   Testing Match...")
                for p in printers:
                    res = job_dispatcher._find_matching_ams_slot(p, j)
                    print(f"     Match with {p.serial}: {res}")

if __name__ == "__main__":
    asyncio.run(debug_dispatch())
