import asyncio
import logging
import sys
import os
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from sqlmodel import select, delete, col, update
from sqlalchemy.orm import selectinload

# Windows AsyncIO Fix
if os.name == 'nt':
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except AttributeError:
        pass

# Add project root
sys.path.append(".")

from app.core.database import async_session_maker
from app.models.core import Printer, PrinterStatusEnum, Job, JobStatusEnum, Product
from app.models.product_sku import ProductSKU 
from app.models.filament import AmsSlot
from app.models.order import Order, OrderItem
# --- FIX: Korrekte Importe aus app/models/ebay.py ---
from app.models.ebay import EbayOrder, EbayLineItem, EbayPricingSummary, EbayPrice, EbayBuyer
from app.services.production.order_processor import order_processor

# Setup
console = Console()
logging.basicConfig(level=logging.ERROR)

async def start_live_test():
    console.print(Panel.fit("[bold red]🚀 LIVE FIRE TEST: eBay Order-to-Physical-Print[/bold red]"))
    console.print("⚠️  [bold yellow]WARNING: This script will clean the DB and move real hardware![/bold yellow]")

    async with async_session_maker() as session:
        
        # ==============================================================================
        # STEP 0: DEEP CLEAN (GHOST & SIMULATION PURGE)
        # ==============================================================================
        console.print("\n[bold]Step 0: Operation Clean Slate (Deep Clean)[/bold]")
        
        # --- A. CLEANUP ORDERS ---
        # Total Purge of all orders, items, and jobs
        console.print("🗑️  Purging all current orders and jobs for a clean state...")
        await session.exec(delete(Job))
        await session.exec(delete(OrderItem))
        await session.exec(delete(Order))
        console.print("   ✅ All orders, order items, and jobs deleted.")
        
        # --- B. CLEANUP SIMULATED PRINTERS ---
        # Lösche alles was mit SIM- beginnt
        stmt_sim = select(Printer).where(col(Printer.serial).startswith("SIM"))
        sim_printers = (await session.exec(stmt_sim)).all()
        
        if sim_printers:
            sim_serials = [p.serial for p in sim_printers]
            console.print(f"🤖 Found {len(sim_serials)} simulated printers. Cleaning up...")
            
            # 1. Unlink Jobs (Foreign Key Fix)
            console.print("   🔗 Unlinking orphaned jobs...")
            stmt_unlink = (
                update(Job)
                .where(col(Job.assigned_printer_serial).in_(sim_serials))
                .values(assigned_printer_serial=None)
            )
            await session.exec(stmt_unlink)

            # 2. Delete Dependencies
            await session.exec(delete(AmsSlot).where(col(AmsSlot.printer_id).in_(sim_serials)))
            await session.exec(delete(Printer).where(col(Printer.serial).in_(sim_serials)))
            
            console.print(f"   🗑️  Deleted printers: {', '.join(sim_serials)}")
        
        # --- C. RESET REAL PRINTERS ---
        # Ensure real printers are IDLE and ready for the test
        console.print("🔄 Resetting real printers to IDLE state...")
        stmt_real = select(Printer).where(~col(Printer.serial).startswith("SIM"))
        real_printers = (await session.exec(stmt_real)).all()
        
        for p in real_printers:
            p.current_status = PrinterStatusEnum.IDLE
            p.current_job_id = None
            p.is_plate_cleared = True
            session.add(p)
            console.print(f"   ✅ Reset [cyan]{p.name}[/cyan] ({p.serial}) to IDLE.")

        await session.commit()
        console.print("✨ System Cleaned. Only Real Data remains (Reset to IDLE).")


        # ==============================================================================
        # STEP 1: HARDWARE CHECK
        # ==============================================================================
        console.print("\n[bold]Step 1: Checking Hardware Readiness[/bold]")
        
        all_printers = (await session.exec(select(Printer))).all()
        if not all_printers:
             console.print("[bold red]❌ CRITICAL: No printers found in DB! (Did you delete the real one?)[/bold red]")
             return
             
        real_printer = None
        for p in all_printers:
            console.print(f"   Found Device: [cyan]{p.name}[/cyan] ({p.serial}) - Status: {p.current_status}")
            # Relaxed check: Just needs to be IDLE
            if p.current_status == PrinterStatusEnum.IDLE:
                real_printer = p
        
        if not real_printer:
            console.print("[bold red]❌ ABORT: No IDLE printers found.[/bold red]")
            return
            
        # Force Plate Cleared flag for test
        if not real_printer.is_plate_cleared:
             console.print("[yellow]⚠️  Printer is IDLE but Plate marked dirty. Forcing clear for test...[/yellow]")
             real_printer.is_plate_cleared = True
             session.add(real_printer)
             await session.commit()

        console.print(f"✅ TARGET ACQUIRED: [green bold]{real_printer.name}[/green bold] (Serial: {real_printer.serial})")

        # ==============================================================================
        # STEP 2: DATA VERIFICATION
        # ==============================================================================
        console.print("\n[bold]Step 2: Verifying SKU Mapping[/bold]")
        prod_query = select(Product).where(Product.name == "Zylinder").options(selectinload(Product.variants))
        prod = (await session.exec(prod_query)).first()
        
        if not prod:
             console.print("[bold red]❌ ABORT: Product 'Zylinder' not found.[/bold red]")
             return

        target_sku_code = None
        for variant in prod.variants:
            if "rot" in variant.name.lower() or "red" in variant.name.lower():
                target_sku_code = variant.sku
                console.print(f"✅ Found Variant: [green]{variant.name}[/green] (SKU: {target_sku_code})")
                break
        
        if not target_sku_code:
             console.print("[bold red]❌ ABORT: No Red variant found for Zylinder.[/bold red]")
             return

        # ==============================================================================
        # STEP 3: LIVE INJECTION
        # ==============================================================================
        console.print("\n[bold]Step 3: Injecting Live Order[/bold]")
        
        new_order_id = f"LIVE-TEST-{int(asyncio.get_event_loop().time())}"
        
        # FIX: Using Correct Pydantic Models & Fields
        mock_ebay_order = EbayOrder(
            order_id=new_order_id,
            creation_date=datetime.now(), 
            last_modified_date=datetime.now(), # Mandatory
            order_payment_status="PAID",       
            order_fulfillment_status="NOT_STARTED",
            buyer=EbayBuyer(username="FactoryAdmin"), 
            pricing_summary=EbayPricingSummary(
                total=EbayPrice(value="0.00", currency="EUR")
            ), 
            line_items=[
                EbayLineItem(
                    sku=target_sku_code,
                    title="Live Test Zylinder Red",
                    quantity=1,
                    line_item_id="LI-1",
                    legacy_item_id="LEGACY-1" # Mandatory
                )
            ]
        )

        await order_processor.process_order(session, mock_ebay_order)
        console.print(f"✅ Order [bold]{new_order_id}[/bold] Injected.")

        # ==============================================================================
        # STEP 4: MONITORING
        # ==============================================================================
        console.print("\n[bold]Step 4: Waiting for Fleet Manager Execution...[/bold]")
        
        # Reload Order to get DB ID
        order_query = select(Order).where(Order.ebay_order_id == new_order_id)
        db_order = (await session.exec(order_query)).first()
        
        if not db_order:
             console.print("[red]❌ Error: Order persistence failed.[/red]")
             return
             
        # Wait for Job creation
        job = None
        for _ in range(5):
            await session.refresh(db_order, ["jobs"])
            if db_order.jobs:
                job = db_order.jobs[0]
                break
            await asyncio.sleep(1)
            
        if not job:
             console.print("[red]❌ Error: Job creation failed. Check OrderProcessor logs.[/red]")
             return

        console.print(f"   👀 Tracking Job ID: [bold]{job.id}[/bold] (Initial Status: {job.status})")

        # Poll loop
        for i in range(30): # 2.5 Minutes
            await session.refresh(job)
            
            if job.status == JobStatusEnum.PRINTING:
                console.print(f"\n[bold green]🚀 SUCCESS! Job {job.id} is now PRINTING on {job.assigned_printer_serial}![/bold green]")
                return
            
            if job.status == JobStatusEnum.FAILED:
                console.print(f"\n[bold red]❌ Job Failed! Error: {job.error_message}[/bold red]")
                return

            if i % 2 == 0:
                console.print(f"   ... Status: {job.status} (Waiting for FleetManager cycle)")
            await asyncio.sleep(5)

        console.print("\n[bold yellow]⚠️ Timeout: Job did not start within 2.5 minutes.[/bold yellow]")
        console.print("Check if AMS slots match (Delta E < 5.0) or if Printer is truly IDLE.")

if __name__ == "__main__":
    asyncio.run(start_live_test())