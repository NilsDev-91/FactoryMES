import asyncio
import logging
import sys
import os
import time
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
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
from app.models.ebay import EbayOrder, EbayLineItem, EbayPricingSummary, EbayPrice, EbayBuyer
from app.services.production.order_processor import order_processor

# Setup
console = Console()
logging.basicConfig(level=logging.ERROR)

async def inject_mock_order(session, skus, label="TEST"):
    """Helper to inject a mock eBay order with multiple SKUs."""
    order_id = f"LIVE-{label}-{int(time.time())}"
    
    line_items = []
    for i, sku in enumerate(skus):
        line_items.append(EbayLineItem(
            sku=sku,
            title=f"Mock Item {i} ({sku})",
            quantity=1,
            line_item_id=f"LI-{label}-{i}",
            legacy_item_id=f"LEGACY-{label}-{i}"
        ))

    mock_ebay_order = EbayOrder(
        order_id=order_id,
        creation_date=datetime.now(), 
        last_modified_date=datetime.now(),
        order_payment_status="PAID",       
        order_fulfillment_status="NOT_STARTED",
        buyer=EbayBuyer(username="FactoryAdmin"), 
        pricing_summary=EbayPricingSummary(
            total=EbayPrice(value="0.00", currency="EUR")
        ), 
        line_items=line_items
    )

    await order_processor.process_order(session, mock_ebay_order)
    return order_id

async def find_target_skus(session):
    """Finds the required SKUs for the test scenario."""
    # Scenario: Zylinder (White, Red) and Zylinder.V2 (Blue)
    targets = [
        {"prod": "Zylinder", "var": "white"},
        {"prod": "Zylinder", "var": "red"},
        {"prod": "Zylinder.V2", "var": "blue"} # Or variant 60mm
    ]
    
    found_skus = []
    
    for t in targets:
        stmt = (
            select(ProductSKU)
            .join(Product)
            .where(Product.name.ilike(f"%{t['prod']}%"))
            .where(ProductSKU.name.ilike(f"%{t['var']}%"))
        )
        res = (await session.exec(stmt)).first()
        if res:
            found_skus.append(res.sku)
            console.print(f"✅ Found Target: [cyan]{t['prod']} - {t['var']}[/cyan] (SKU: {res.sku})")
        else:
            console.print(f"⚠️  Missing Target: {t['prod']} - {t['var']}")

    # Fallback: if we didn't find all 3 items, just find any 3 distinct SKUs
    if len(found_skus) < 3:
        console.print("[yellow]Using fallback: Finding any 3 distinct SKUs to satisfy test requirements...[/yellow]")
        stmt_fallback = select(ProductSKU).limit(5)
        all_skus = (await session.exec(stmt_fallback)).all()
        found_skus = list(set([s.sku for s in all_skus]))[:3]
        
    return found_skus

async def start_live_test():
    console.print(Panel.fit("[bold red]🚀 LIVE FIRE TEST V2: Advanced Multi-Order Simulation[/bold red]"))
    console.print("⚠️  [bold yellow]WARNING: This script will clean the DB and move real hardware![/bold yellow]")

    async with async_session_maker() as session:
        
        # STEP 0: DEEP CLEAN
        console.print("\n[bold]Step 0: Operation Clean Slate[/bold]")
        await session.exec(delete(Job))
        await session.exec(delete(OrderItem))
        await session.exec(delete(Order))
        
        # Reset real printers
        stmt_real = select(Printer).where(~col(Printer.serial).startswith("SIM"))
        real_printers = (await session.exec(stmt_real)).all()
        for p in real_printers:
            p.current_status = PrinterStatusEnum.IDLE
            p.current_job_id = None
            p.is_plate_cleared = True
            session.add(p)
        await session.commit()
        console.print("   ✅ System Purged and Real Printers reset to IDLE.")

        # STEP 1: HARDWARE CHECK
        console.print("\n[bold]Step 1: Hardware Readiness[/bold]")
        real_printer = (await session.exec(select(Printer).where(Printer.current_status == PrinterStatusEnum.IDLE))).first()
        if not real_printer:
            console.print("[red]❌ ABORT: No IDLE printers found.[/red]")
            return
        console.print(f"✅ TARGET: [green bold]{real_printer.name}[/green bold]")

        # STEP 2: SKU LOOKUP
        console.print("\n[bold]Step 2: Locating Test SKUs[/bold]")
        skus = await find_target_skus(session)
        if len(skus) < 3:
            console.print("[red]❌ ABORT: Could not find enough SKUs for test sequence.[/red]")
            return

        # STEP 3: ORDER INJECTION
        console.print("\n[bold]Step 3: Sequential Order Injection[/bold]")
        
        # Order A: The Mix (White + Red)
        order_a_id = await inject_mock_order(session, skus[0:2], "MIX")
        console.print(f"📥 [bold]Order A (The Mix)[/bold] injected: {order_a_id} (SKUs: {', '.join(skus[0:2])})")
        
        console.print("⏳ Simulating traffic... Waiting 15 seconds before next order.")
        await asyncio.sleep(15)
        
        # Order B: The Tower (Blue / V2)
        order_b_id = await inject_mock_order(session, [skus[2]], "TOWER")
        console.print(f"📥 [bold]Order B (The Tower)[/bold] injected: {order_b_id} (SKU: {skus[2]})")

        # STEP 4: ADVANCED MONITORING
        console.print("\n[bold]Step 4: Advanced Job Monitoring[/bold]")
        
        for i in range(40): # ~6.5 minutes polling
            await session.commit() # Refresh session
            
            stmt_jobs = select(Job).join(Order).where(col(Order.ebay_order_id).in_([order_a_id, order_b_id]))
            current_jobs = (await session.exec(stmt_jobs)).all()
            
            table = Table(title=f"Production Pipeline State (Update {i+1})")
            table.add_column("Job ID", style="cyan")
            table.add_column("SKU", style="magenta")
            table.add_column("Status", style="bold")
            table.add_column("Printer", style="green")
            
            done_count = 0
            for j in current_jobs:
                # Find SKU for this job (simplified for mock requirements)
                req = j.filament_requirements[0] if j.filament_requirements else {}
                sku_label = f"{req.get('material', '???')} - {req.get('hex_color', '???')}"
                
                status_color = "white"
                if j.status == JobStatusEnum.PRINTING: 
                    status_color = "green"
                    done_count += 1
                elif j.status == JobStatusEnum.FAILED: 
                    status_color = "red"
                elif j.status == JobStatusEnum.UPLOADING: 
                    status_color = "yellow"
                
                table.add_row(
                    str(j.id), 
                    sku_label, 
                    f"[{status_color}]{j.status}[/{status_color}]", 
                    j.assigned_printer_serial or "---"
                )
            
            console.clear()
            console.print(Panel.fit("[bold red]🚀 LIVE FIRE MONITORING[/bold red]"))
            console.print(table)
            
            if len(current_jobs) >= 3 and done_count >= 3:
                console.print("\n[bold green]🏁 MISSION ACCOMPLISHED: All 3 jobs are PRINTING![/bold green]")
                return
            
            await asyncio.sleep(10)

        console.print("\n[bold yellow]⚠️  Timeout: Not all jobs reached PRINTING state.[/bold yellow]")

if __name__ == "__main__":
    asyncio.run(start_live_test())