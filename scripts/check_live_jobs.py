
import asyncio
import json
from sqlmodel import select
from app.core.database import async_session_maker
from app.models.core import Job, Printer
from app.models.filament import AmsSlot

async def main():
    async with async_session_maker() as session:
        # Jobs
        stmt = select(Job).order_by(Job.id.desc()).limit(5)
        jobs = (await session.execute(stmt)).scalars().all()
        
        job_list = []
        for job in jobs:
            job_list.append({
                "id": job.id,
                "status": str(job.status),
                "printer": job.assigned_printer_serial,
                "requirements": job.filament_requirements,
                "metadata": job.job_metadata,
                "gcode": job.gcode_path
            })
            
        # AMS Slots
        stmt_ams = select(AmsSlot)
        slots = (await session.execute(stmt_ams)).scalars().all()
        slot_list = []
        for slot in slots:
            slot_list.append({
                "printer": slot.printer_id,
                "slot_id": slot.slot_id,
                "color": slot.color_hex,
                "material": slot.material
            })

        output = {
            "jobs": job_list,
            "ams": slot_list
        }
            
        with open("scripts/job_full_dump.json", "w") as f:
            json.dump(output, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
