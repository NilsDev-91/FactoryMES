import asyncio
import sys
import os
import logging
from rich.console import Console
from sqlalchemy import select, delete

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker
from app.models.order import Order, OrderItem
from app.models.core import Job, Printer, PrinterStatusEnum, JobStatusEnum
from app.models.product_sku import ProductSKU
from app.services.production.order_processor import order_processor
from app.services.production.dispatcher import ProductionDispatcher

console = Console()

async def run_full_verification():
    console.rule("[bold cyan]FactoryOS E2E Verification")
    
    async with async_session_maker() as session:
        # 1. PURGE
        console.log("🧹 Purging old data...")
        await session.execute(delete(Job))
        await session.execute(delete(OrderItem))
        await session.execute(delete(Order))
        
        # 2. RESET PRINTER
        printer_stmt = select(Printer).where(Printer.serial == "03919C461802608")
        res = await session.execute(printer_stmt)
        printer = res.scalars().first()
        if printer:
            console.log(f"🔄 Resetting Printer {printer.serial}...")
            printer.current_status = PrinterStatusEnum.IDLE
            printer.is_plate_cleared = True
            printer.current_job_id = None
            session.add(printer)
        
        await session.commit()

        # 3. INJECT ORDER
        console.log("📥 Injecting Order...")
        new_order = Order(
            ebay_order_id="E2E-TEST-001",
            buyer_username="e2e_tester",
            total_price=10.0,
            currency="USD",
            status="PENDING"
        )
        session.add(new_order)
        await session.flush()
        
        item = OrderItem(
            order_id=new_order.id,
            sku="ZYlinder-v2-PLA-FF0000", # Valid SKU
            title="Zylinder V2 E2E Test",
            quantity=1
        )
        session.add(item)
        await session.commit()
        console.log(f"✅ Order {new_order.id} injected.")

    # 4. MANUALLY RUN PROCESSOR
    console.log("🧠 Running OrderProcessor sync...")
    await order_processor.sync_local_orders()
    
    # 5. VERIFY JOB CREATION
    async with async_session_maker() as session:
        job_stmt = select(Job).where(Job.order_id == new_order.id)
        res = await session.execute(job_stmt)
        job = res.scalars().first()
        if job:
            console.log(f"✅ Job {job.id} created for order.")
        else:
            console.log("❌ FAILED: Job was not created!")
            return

    # 6. MANUALLY RUN DISPATCHER
    console.log("🚀 Running JobDispatcher cycle...")
    dispatcher = ProductionDispatcher()
    # Note: dispatcher.run_cycle calls self.job_dispatcher.dispatch_next_job(session)
    await dispatcher.run_cycle()

    # 7. FINAL VERIFICATION
    async with async_session_maker() as session:
        res = await session.execute(job_stmt)
        job = res.scalars().first()
        
        res = await session.execute(printer_stmt)
        printer = res.scalars().first()
        
        if job and job.status in [JobStatusEnum.PRINTING, JobStatusEnum.UPLOADING]:
            print(f"FINAL_RESULT: JOB_SUCCESS | ID: {job.id} | Status: {job.status}")
        else:
            print(f"FINAL_RESULT: JOB_FAILED | Status: {job.status if job else 'NOT_FOUND'}")
            
        if printer and printer.current_status == PrinterStatusEnum.PRINTING:
            print(f"FINAL_RESULT: PRINTER_SUCCESS | Status: {printer.current_status}")
        else:
            print(f"FINAL_RESULT: PRINTER_FAILED | Status: {printer.current_status if printer else 'NOT_FOUND'}")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_full_verification())
