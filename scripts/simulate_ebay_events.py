import asyncio
import time
import logging
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import select, delete
from sqlalchemy.orm import selectinload
from app.core.database import async_session_maker
from app.models.order import Order, OrderItem
from app.models.core import Job, Printer, PrinterStatusEnum, JobStatusEnum
from app.models.product_sku import ProductSKU

# RICH formatting if available, otherwise fallback
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.status import Status
    console = Console()
except ImportError:
    class MockConsole:
        def print(self, msg, **kwargs): print(msg)
        def log(self, msg, **kwargs): print(msg)
        def status(self, msg): return self
        def __enter__(self): return self
        def __exit__(self, *args): pass
    console = MockConsole()

async def simulate_ebay_events():
    """
    STRICT EXTERNAL SOURCE SIMULATOR
    Acts as the eBay API pushing events into the DB.
    Ensures OrderProcessor handles the conversion to Jobs.
    """
    console.print(Panel.fit("[bold blue]eBay Order Simulation 2.0[/bold blue]\n[italic]Testing Automated Order-to-Job conversion...[/italic]"))
    
    order_id = "Test-Order-Auto-111"
    sku_val = "KEGEL-V3-BLACK"
    
    async with async_session_maker() as session:
        # STEP 1: PURGE (for clean test)
        console.log("🧹 [CLEANUP] Purging existing Orders and Jobs...")
        await session.exec(delete(Job))
        await session.exec(delete(OrderItem))
        await session.exec(delete(Order))
        
        # STEP 1.1: Reset Printer - SKIPPED BY USER REQUEST
        console.log("ℹ️ [RESET] Printer state reset disabled.")

        # STEP 2: INJECT ORDER (External Event Simulation)
        console.log(f"📥 [INJECT] Creating Order '{order_id}'...")
        
        db_order = Order(
            ebay_order_id=order_id,
            buyer_username="EBAY_SIMULATOR",
            total_price=24.99,
            currency="EUR",
            status="PENDING"
        )
        session.add(db_order)
        await session.flush()
        
        db_item = OrderItem(
            order_id=db_order.id,
            sku=sku_val,
            title="Zylinder V2 (Simulated)",
            quantity=1
        )
        session.add(db_item)
        await session.commit()
        
        console.print(f"[EVENT] 📦 Simulated eBay Order '{order_id}' injected.")
        console.print(f"      (SKU: {sku_val} | Source: INJECTED_ORPHAN)")
        console.print(f"      [italic]The OrderProcessor service will now pick this up and create Jobs.[/italic]\n")

    # STEP 3: MONITORING
    console.print("[bold yellow]🔍 PASSIVE MONITORING STARTED[/bold yellow]")
    
    jobs_detected = False
    printer_assigned = False
    
    while True:
        await asyncio.sleep(2)
        async with async_session_maker() as session:
            # Refresh Jobs
            job_stmt = select(Job).options(selectinload(Job.order)).where(Job.order_id == db_order.id)
            jobs = (await session.exec(job_stmt)).all()
            
            if jobs and not jobs_detected:
                jobs_detected = True
                console.print(f"[PROCESSOR] ✅ OrderProcessor created {len(jobs)} Job(s)!")
            
            for job in jobs:
                if job.assigned_printer_serial and not printer_assigned:
                    printer_assigned = True
                    console.print(f"[DISPATCH] 🖨️ Assigned to Printer: [bold cyan]{job.assigned_printer_serial}[/bold cyan]")
                    # Observe metadata inheritance (Verify the "Brain" worked)
                    height = job.job_metadata.get("part_height_mm")
                    console.print(f"[METADATA] 🧩 Verification: Job inherited Height={height}mm")

                if job.status == JobStatusEnum.PRINTING:
                    console.print(f"\n🚀 [bold green]PRINTER STARTED![/bold green] Job {job.id} is now PRINTING.")
                    return
                
                if job.status == JobStatusEnum.FAILED:
                    console.print(f"\n❌ [bold red]JOB FAILED:[/bold red] {job.error_message}")
                    return
            
            if not jobs_detected:
                 console.log(f"Waiting for OrderProcessor... (Order: {order_id})")
            else:
                 status_str = jobs[0].status.value if jobs else "N/A"
                 assigned_str = jobs[0].assigned_printer_serial or "None"
                 console.log(f"Job Status: [bold]{status_str}[/bold] | Assigned: {assigned_str}")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(simulate_ebay_events())
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped by user.")
