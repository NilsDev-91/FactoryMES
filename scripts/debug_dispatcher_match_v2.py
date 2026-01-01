import asyncio
import os
import sys
from sqlmodel import select
from sqlalchemy.orm import selectinload

# Add project root
sys.path.append(".")

from app.core.database import async_session_maker
from app.models.core import Job, Printer
from app.services.job_dispatcher import JobDispatcher

async def debug_match():
    output = []
    async with async_session_maker() as session:
        # Load Latest Job
        stmt_job = select(Job).order_by(Job.id.desc()).limit(1)
        job = (await session.exec(stmt_job)).first()
        
        # Load Real Printer
        stmt_printer = select(Printer).where(Printer.serial == "03919C461802608").options(selectinload(Printer.ams_slots))
        printer = (await session.exec(stmt_printer)).first()
        
        if not job or not printer:
            output.append("Missing data.")
        else:
            output.append(f"DEBUGGING MATCH: Job {job.id} -> Printer {printer.serial}")
            output.append(f"Job Req: {job.filament_requirements}")
            output.append(f"Printer Status: {printer.current_status}, Cleared: {printer.is_plate_cleared}")
            
            dispatcher = JobDispatcher()
            
            # Manual trace of _find_matching_ams_slot
            req = job.filament_requirements[0]
            req_material = req.get("material")
            req_color = req.get("hex_color") or req.get("color")
            
            output.append(f"Parsed Req: Material={req_material}, Color={req_color}")
            
            for slot in printer.ams_slots:
                output.append(f"\nChecking Slot {slot.slot_id}: Material='{slot.material}', Color='{slot.color_hex}'")
                
                # Rule: Material Match
                if not slot.material or slot.material.upper() != req_material.upper():
                    output.append(f"   FAIL: Material mismatch ('{slot.material}' != '{req_material}')")
                    continue
                
                # Rule: Color Match
                from app.services.logic.color_matcher import color_matcher
                match = color_matcher.is_color_match(req_color, slot.color_hex)
                output.append(f"   Color Match result: {match}")
                
                if match:
                    output.append("   SUCCESS: Found match!")
                    break
            else:
                output.append("\nNO MATCH FOUND.")

    with open("debug_dispatch_result.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output))

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(debug_match())
