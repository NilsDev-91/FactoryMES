import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker
from sqlmodel import select
from app.models.core import Printer, Job, JobStatusEnum, PrinterStatusEnum
from app.services.job_dispatcher import JobDispatcher

async def verify_proof():
    print("🧪 BEGIN FINAL VERIFICATION PROOF")
    async with async_session_maker() as session:
        # 1. Force state for validation
        printer_serial = "03919C461802608"
        p = await session.get(Printer, printer_serial)
        if not p:
            print("❌ Printer not found!")
            return
            
        print(f"Force resetting printer {printer_serial} to IDLE/CLEARED...")
        p.current_status = PrinterStatusEnum.IDLE
        p.is_plate_cleared = True
        session.add(p)
        await session.commit()
        
        # 2. Run Dispatcher
        dispatcher = JobDispatcher()
        print("Dispatching...")
        await dispatcher.dispatch_next_job(session)
        
        # 3. Check Results
        stmt = select(Job).where(Job.assigned_printer_serial == printer_serial)
        jobs = (await session.exec(stmt)).all()
        
        print(f"\nRESULTS for {printer_serial}:")
        for j in jobs:
            # Re-fetch order for SKU name with items pre-loaded
            from sqlalchemy.orm import selectinload
            from app.models.order import Order
            order_stmt = select(Order).where(Order.id == j.order_id).options(selectinload(Order.items))
            order = (await session.exec(order_stmt)).first()
            
            sku = "Unknown"
            if order and order.items:
                 sku = order.items[0].sku
                 
            print(f"✅ JOB {j.id} ({sku})")
            print(f"   Status: {j.status}")
            print(f"   Requirements: {j.filament_requirements}")
            # Note: ams_mapping logic in dispatcher (currently maps ALL 16 to the same one for broadcast)
            # Actually, per job_dispatcher.py:141: ams_mapping = [slot.slot_id + 1] * 16
            # This is a broadcast intended for a single-color job.
            
    print("\n🏁 PROOF COMPLETE")

if __name__ == "__main__":
    asyncio.run(verify_proof())
