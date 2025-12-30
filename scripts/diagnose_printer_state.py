import asyncio
import os
import sys

# Ensure app modules are found
sys.path.append(os.getcwd())

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload

from app.core.config import settings
from app.models.core import Printer, Job, JobStatusEnum
from app.services.logic.filament_manager import calculate_delta_e_2000

async def diagnose_printer_state():
    print("🔌 Connecting to Database...")
    engine = create_async_engine(settings.ASYNC_DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 1. Fetch Printer
        stmt = select(Printer).where(Printer.serial.startswith("03919C")).options(selectinload(Printer.ams_slots))
        printer = (await session.exec(stmt)).first()
        
        if not printer:
            # Fallback
            printer = (await session.exec(select(Printer))).first()
            
        if not printer:
            print("❌ CRITICAL: No printer found in DB.")
            return

        print(f"\n📠 PRINTER DIAGNOSTIC: {printer.name} ({printer.serial})")
        print(f"   Status: {printer.current_status} (Expected: IDLE)")
        print(f"   Is Plate Cleared: {printer.is_plate_cleared} (Expected: True)")

        
        print("\n🧵 AMS SLOTS (DB State):")
        if not printer.ams_slots:
            print("   ⚠️  No AMS Slots found in DB!")
        
        for slot in printer.ams_slots:
            print(f"   [Slot {slot.ams_index}/{slot.slot_index}] Color: '{slot.tray_color}' Type: '{slot.tray_type}' Remain: {slot.remaining_percent}%")

        # 2. Fetch Oldest Pending Job
        job_stmt = (
            select(Job)
            .where(Job.status == JobStatusEnum.PENDING)
            .order_by(Job.created_at)
        )
        job = (await session.exec(job_stmt)).first()
        
        if not job:
            print("\n❌ NO PENDING JOBS found to test match against.")
            return
            
        print(f"\n📦 OLDEST PENDING JOB: Job {job.id}")
        print(f"   Filament Reqs: {job.filament_requirements}")
        
        # 3. Simulate Match
        print("\n🧮 FMS MATCH SIMULATION (Delta E):")
        
        if not job.filament_requirements:
             print("   ⚠️ Job has no filament requirements.")
             return

        # Assuming single filament for simplicity of this script, or iterating
        reqs = job.filament_requirements if isinstance(job.filament_requirements, list) else [job.filament_requirements]
        
        for i, req in enumerate(reqs):
            req_color = req.get('hex_color')
            req_material = req.get('material', 'PLA')
            print(f"   Requirement #{i+1}: {req_material} @ {req_color}")
            
            match_found = False
            best_de = 999.0
            
            for slot in printer.ams_slots:
                # Type Check
                if not slot.tray_type or slot.tray_type.lower() != req_material.lower():
                    continue

                # Color Check
                if not slot.tray_color:
                    continue
                    
                de = calculate_delta_e_2000(req_color, slot.tray_color)
                print(f"      vs Slot {slot.ams_index}/{slot.slot_index} ({slot.tray_color}): dE = {de:.4f}")
                
                if de < 5.0 and de < best_de:
                    best_de = de
                    match_found = True
                    print(f"         ✅ MATCH (dE < 5.0)")
            
            if not match_found:
                print(f"      ❌ NO MATCHING SLOT FOUND for this requirement.")

if __name__ == "__main__":
    asyncio.run(diagnose_printer_state())
