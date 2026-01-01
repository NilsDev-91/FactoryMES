import asyncio
import os
import sys
import logging
import time
from datetime import datetime, timezone
from sqlmodel import select, delete
from sqlalchemy.orm import selectinload
from rich.console import Console
from rich.panel import Panel

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import async_session_maker
from app.models.core import Product, Job, Printer, PrinterTypeEnum, PrinterStatusEnum, JobStatusEnum
from app.models.product_sku import ProductSKU
from app.models.filament import AmsSlot
from app.models.order import Order as InternalOrder
from app.models.ebay import EbayOrder, EbayLineItem, EbayBuyer, EbayPricingSummary, EbayPrice as InternalEbayPrice
from app.services.production.order_processor import OrderProcessor
from app.services.job_executor import executor as job_executor

console = Console()

# Configure Logging
logging.basicConfig(level=logging.INFO)
logging.getLogger("aiomqtt").setLevel(logging.WARNING)
logging.getLogger("app.services.printer.commander").setLevel(logging.INFO)

async def simulate_ebay_flow():
    console.print(Panel.fit("[bold green]eBay Order-to-Print Full Pipeline Simulation[/bold green]"))
    
    async with async_session_maker() as session:
        # 1. Setup Data & Verify Zylinder
        console.print("\n[bold]Stage 1: Logic Verification & Data Audit[/bold]")
        
        stmt = select(Product).where(Product.name == "Zylinder")
        product = (await session.execute(stmt)).scalars().first()
        if not product:
            console.print("[red]-- Error: 'Zylinder' product not found. Run seed_zylinder_skus.py first.[/red]")
            return

        stmt = select(ProductSKU).where(ProductSKU.sku == "ZYL-RED").options(selectinload(ProductSKU.print_file))
        sku = (await session.execute(stmt)).scalars().first()
        if not sku:
             console.print("[red]-- Error: SKU 'ZYL-RED' not found.[/red]")
             return
        
        console.print(f"[green]SUCCESS: Zylinder Data Verified. Target SKU: {sku.sku}[/green]")
        expected_path = sku.print_file.file_path if sku.print_file else None
        target_color = sku.hex_color

        # 2. Mock eBay Order
        console.print("\n[bold]Stage 2: eBay Mock Injection[/bold]")
        order_id = f"EBAY-SIM-{int(time.time())}-RED"
        mock_ebay_order = EbayOrder(
            orderId=order_id,
            creationDate=datetime.now(timezone.utc),
            lastModifiedDate=datetime.now(timezone.utc),
            orderPaymentStatus="PAID",
            orderFulfillmentStatus="FULFILLED",
            buyer=EbayBuyer(username="Test-User"),
            pricingSummary=EbayPricingSummary(total=InternalEbayPrice(value="19.99", currency="USD")),
            lineItems=[
                EbayLineItem(
                    lineItemId="ITEM-001",
                    legacyItemId="LEGACY-001",
                    sku="ZYL-RED",
                    quantity=1,
                    title="3D Printed Zylinder - Red"
                )
            ]
        )
        
        # 3. Process Order
        processor = OrderProcessor()
        console.print("[cyan]Calling OrderProcessor.process_order()...[/cyan]")
        await processor.process_order(session, mock_ebay_order)
            
        # 4. ASSERTIONS: Check Job
        console.print("\n[bold]Stage 3: Pipeline Assertions[/bold]")
        
        # We need to refresh or re-query to find the newly created job
        stmt = (
            select(Job)
            .join(InternalOrder)
            .where(InternalOrder.ebay_order_id == order_id)
            .options(selectinload(Job.order))
        )
        job = (await session.execute(stmt)).scalars().first()
        
        if not job:
            console.print("[red]-- ASSERTION FAILED: Job was not created in DB.[/red]")
            return
        
        console.print(f"[green]SUCCESS: Job Created (ID: {job.id})[/green]")
        
        if job.gcode_path == expected_path:
            console.print(f"[green]SUCCESS: Job File Path Matches: {job.gcode_path}[/green]")
        else:
            console.print(f"[red]-- ASSERTION FAILED: Job File Path ({job.gcode_path}) does not match expected ({expected_path}).[/red]")
        
        reqs = job.filament_requirements
        if isinstance(reqs, list) and len(reqs) > 0 and (reqs[0].get("color") == target_color or reqs[0].get("hex_color") == target_color):
             console.print(f"[green]SUCCESS: Job Filament Requirements contain {target_color}[/green]")
        else:
             console.print(f"[red]-- ASSERTION FAILED: Job Filament Requirements ({reqs}) invalid or missing color {target_color}.[/red]")

        # 5. Execute Print (The Loop)
        console.print("\n[bold]Stage 4: Execution & State Transition[/bold]")
        
        # Setup SIM-A1 printer
        serial = "SIM-A1-EBAY"
        printer = await session.get(Printer, serial)
        if not printer:
            printer = Printer(
                serial=serial,
                name="Simulator A1",
                type=PrinterTypeEnum.A1
            )
            session.add(printer)
        
        printer.current_status = PrinterStatusEnum.IDLE
        printer.is_plate_cleared = True
        printer.ip_address = "127.0.0.1" # Trigger simulation mode in Commander
        printer.access_code = "SIM-CODE"
        
        # Cleanup ams slots for this serial
        await session.execute(delete(AmsSlot).where(AmsSlot.printer_id == serial))
        await session.flush()
        
        # Setup Red Filament in AMS Slot 1
        red_slot = AmsSlot(
            printer_id=printer.serial,
            ams_index=0,
            slot_index=0,
            slot_id=0,
            color_hex=target_color,
            material="PLA",
            remaining_percent=100
        )
        session.add(red_slot)
        await session.commit()
        console.print(f"[green]SUCCESS: Printer {serial} setup with Red PLA in Slot 1.[/green]")

        # Run Loop
        console.print("[cyan]Triggering JobExecutor.process_queue()...[/cyan]")
        # We need to use the session we have, but process_queue creates its own.
        # That's fine as long as we commit before and refresh after.
        await job_executor.process_queue()
        
        # Verify Results
        await session.refresh(printer)
        session.expire(job) # Force reload
        
        # Re-query printer to be absolutely sure
        stmt = select(Printer).where(Printer.serial == serial)
        printer = (await session.execute(stmt)).scalars().first()
        
        if printer.current_status == PrinterStatusEnum.PRINTING:
            console.print("[bold green]SUCCESS: Printer Status changed to PRINTING.[/bold green]")
        else:
            console.print(f"[red]-- FAILURE: Printer Status is {printer.current_status}, expected PRINTING.[/red]")
            
        # Check Job status via fresh query
        stmt = select(Job).join(InternalOrder).where(InternalOrder.ebay_order_id == order_id)
        job = (await session.execute(stmt)).scalars().first()
        if job.status == JobStatusEnum.PRINTING:
            console.print(f"[green]SUCCESS: Job Status: {job.status}[/green]")
        else:
            console.print(f"[red]-- Job Status is {job.status}, expected PRINTING.[/red]")

    console.print(f"\n[bold green]Simulation Finished Successfully.[/bold green]\n")

if __name__ == "__main__":
    import traceback
    try:
        if os.name == 'nt':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(simulate_ebay_flow())
    except Exception:
        traceback.print_exc()
        sys.exit(1)
