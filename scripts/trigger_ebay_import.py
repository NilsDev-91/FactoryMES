import asyncio
import logging
import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import delete
from sqlalchemy.orm import selectinload
from sqlmodel import select

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import async_session_maker
from app.models.core import Job, JobStatusEnum, Printer, OrderStatusEnum, Product
from app.models.order import Order, OrderItem
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

async def trigger_ebay_import():
    console.print(Panel.fit("[bold blue]eBay Order Simulation Trigger[/bold blue]\n[italic]Simulating raw database injection...[/italic]"))
    
    order_id_str = "Test-Order111"
    sku_val = "ZYlinder-v2-PLA-FF0000" # Corrected SKU

    async with async_session_maker() as session:
        # STEP 1: CLEAN UP
        console.log("🧹 [CLEANUP] Removing stale data for 'Test-Order111'...")
        # Since Job has a foreign key to Order, and we want a clean slate:
        # Use select to find existing order first to handle related jobs manually if needed, 
        # or rely on CASCADE if configured.
        stmt_old = select(Order).where(Order.ebay_order_id == order_id_str)
        old_order_res = await session.exec(stmt_old)
        old_order = old_order_res.first()
        if old_order:
            # Delete Job manually if needed, or rely on cascade
            # To be safe, we'll explicitly delete jobs linked to this order
            await session.execute(delete(Job).where(Job.order_id == old_order.id))
            await session.delete(old_order)
            await session.commit()

        # STEP 2: INJECT EVENT
        console.log(f"📥 [INJECT] Creating Order '{order_id_str}'...")

        # ENSURE PRODUCT HEIGHT (for A1_GANTRY_SWEEP strategy)
        # Find the product associated with this SKU
        sku_stmt = select(ProductSKU).where(ProductSKU.sku == sku_val)
        sku_obj = (await session.exec(sku_stmt)).first()
        if sku_obj and sku_obj.product_id:
            product = await session.get(Product, sku_obj.product_id)
            if product:
                if product.part_height_mm != 120.0:
                    console.log(f"📏 [HEIGHT] Setting height to 120.0mm for Product '{product.name}'...")
                    product.part_height_mm = 120.0
                    session.add(product)

        order = Order(
            ebay_order_id=order_id_str,
            buyer_username="EBAY_SIMULATOR",
            total_price=49.99,
            currency="USD",
            status="PENDING" # Using raw string as requested, though OrderStatusEnum.OPEN is standard
        )
        session.add(order)
        await session.flush() # Get order.id
        
        item = OrderItem(
            order_id=order.id,
            sku=sku_val,
            title="Zylinder V2 (Simulated)",
            quantity=1
        )
        session.add(item)
        await session.commit()
        
        # STEP 3: CREATE JOB (Bridge the Order-to-Job gap)
        # Directly creating the Job ensures the Dispatcher picks it up immediately
        # even if the background OrderProcessor is not running or on a long loop.
        console.log("🛠️ [JOB] Manually creating Job for Order...")
        
        # Use the Zylinder V2 Master file found in storage
        v2_3mf_path = "storage/3mf/ba4cc7f8-649c-48c4-9947-15cd68c6a854.3mf"
        
        job = Job(
            order_id=order.id,
            gcode_path=v2_3mf_path,
            status=JobStatusEnum.PENDING,
            priority=10,
            filament_requirements=[{
                "material": "PLA",
                "color": "#FF0000"
            }],
            job_metadata={
                "part_height_mm": 120.0,
                "is_continuous": True
            }
        )
        session.add(job)
        await session.commit()
        
        console.print(f"[EVENT] 📦 Simulated eBay Order '{order_id_str}' injected.")
        console.print(f"      (SKU: {sku_val} | Job: {job.id} | Status: PENDING)")

    # STEP 4: PASSIVE MONITORING
    console.print("\n[bold yellow]🔍 PASSIVE MONITORING STARTED[/bold yellow]")
    console.print(f"Waiting for Dispatcher to assign Job {job.id}...")
    
    printer_assigned = False
    
    while True:
        await asyncio.sleep(2)
        async with async_session_maker() as session:
            # Refresh Job
            job_stmt = select(Job).where(Job.id == job.id)
            job_res = await session.exec(job_stmt)
            job_obj = job_res.first()
            
            if not job_obj:
                console.log("[ERROR] Job disappeared!")
                break
                
            if job_obj.assigned_printer_serial and not printer_assigned:
                printer_assigned = True
                console.print(f"[DISPATCH] 🖨️ Assigned to Printer: [bold cyan]{job_obj.assigned_printer_serial}[/bold cyan]")
                # Check for strategy
                strategy = job_obj.job_metadata.get("strategy_used") or "A1_GANTRY_SWEEP (Expected)"
                console.print(f"[STRATEGY] 🧠 Strategy Selected: {strategy}")

            if job_obj.status == JobStatusEnum.PRINTING:
                console.print(f"\n🚀 [bold green]PRINTER STARTED![/bold green] Job {job_obj.id} is now PRINTING.")
                break
            
            if job_obj.status == JobStatusEnum.FAILED:
                console.print(f"\n❌ [bold red]JOB FAILED:[/bold red] {job_obj.error_message}")
                break
            
            # Slow log to show we are alive
            console.log(f"Status: [bold]{job_obj.status}[/bold] | Assigned: {job_obj.assigned_printer_serial or 'None'}")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(trigger_ebay_import())
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped by user.")
