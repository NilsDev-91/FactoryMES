
import asyncio
import sys
import os
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import async_session_maker
from app.models.core import Printer, Job, JobStatusEnum, PrinterStatusEnum
from app.services.logic.color_matcher import color_matcher

async def debug_fms_state():
    printer_serial = "03919C461802608"
    
    async with async_session_maker() as session:
        # 1. Fetch Printer
        print(f"--- FMS DEBUG: Printer {printer_serial} ---")
        stmt = (
            select(Printer)
            .where(Printer.serial == printer_serial)
            .options(selectinload(Printer.ams_slots))
        )
        printer = (await session.execute(stmt)).scalars().first()
        
        if not printer:
            print(f"❌ Printer {printer_serial} not found in database!")
            return

        print(f"Status: {printer.current_status}")
        print(f"Plate Cleared: {printer.is_plate_cleared}")
        print("\nAMS SLOTS (DB State):")
        for slot in sorted(printer.ams_slots, key=lambda s: s.slot_id):
            print(f"  [Slot {slot.slot_id}] {slot.material or 'Unknown'} - {slot.color_hex or 'None'}")

        # 2. Fetch Pending Jobs
        print("\n--- PENDING JOBS ---")
        job_stmt = (
            select(Job)
            .where(Job.status == JobStatusEnum.PENDING)
            .order_by(Job.priority.desc())
        )
        pending_jobs = (await session.execute(job_stmt)).scalars().all()
        
        if not pending_jobs:
            print("No pending jobs found.")
            return

        for job in pending_jobs:
            reqs = job.filament_requirements
            print(f"  [Job {job.id}] Priority: {job.priority}")
            if not reqs:
                print("    ❌ No filament requirements!")
                continue
            
            for i, req in enumerate(reqs):
                req_material = req.get("material")
                req_color = req.get("hex_color")
                print(f"    Requirement {i}: {req_material} - {req_color}")

                # 3. Simulate Matching
                print(f"    Simulating matches for {req_material}/{req_color}:")
                for slot in printer.ams_slots:
                    # Material Check
                    material_match = slot.material and req_material and slot.material.upper() == req_material.upper()
                    
                    # Color Check
                    delta_e = 999.0
                    color_match = False
                    if slot.color_hex and req_color:
                        try:
                            rgb1 = color_matcher.hex_to_rgb(req_color)
                            rgb2 = color_matcher.hex_to_rgb(slot.color_hex)
                            lab1 = color_matcher.rgb_to_lab(*rgb1)
                            lab2 = color_matcher.rgb_to_lab(*rgb2)
                            delta_e = color_matcher.delta_e_cie2000(lab1, lab2)
                            color_match = delta_e <= 5.0
                        except Exception as e:
                            print(f"      [Slot {slot.slot_id}] Error: {e}")

                    status = "✅ MATCH" if (material_match and color_match) else "❌ NO MATCH"
                    notes = []
                    if not material_match: notes.append(f"Material Mismatch ({slot.material} vs {req_material})")
                    if not color_match: notes.append(f"Color Mismatch (ΔE={delta_e:.2f})")
                    
                    print(f"      [Slot {slot.slot_id}] {status} | ΔE: {delta_e:.2f} | {', '.join(notes)}")

if __name__ == "__main__":
    asyncio.run(debug_fms_state())
