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

# Add project root
sys.path.append(".")

from app.core.database import async_session_maker
from app.models.core import Printer, PrinterStatusEnum, Job, JobStatusEnum, Product
from app.models.product_sku import ProductSKU 
from app.models.order import Order, OrderItem
from app.models.ebay import EbayOrder, EbayLineItem, EbayPricingSummary, EbayPrice, EbayBuyer
from app.services.production.order_processor import order_processor

# Setup
console = Console()
logging.basicConfig(level=logging.ERROR)

async def inject_mock_order(session, skus, label="SPEC"):
    """Helper to inject a mock eBay order."""
    order_id = f"LIVE-{label}-{int(time.time())}"
    
    line_items = []
    for i, sku in enumerate(skus):
        line_items.append(EbayLineItem(
            sku=sku,
            title=f"Specific Item {sku}",
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
        buyer=EbayBuyer(username="FactoryQA"), 
        pricing_summary=EbayPricingSummary(
            total=EbayPrice(value="0.00", currency="EUR")
        ), 
        line_items=line_items
    )

    await order_processor.process_order(session, mock_ebay_order)
    return order_id

async def start_specific_test():
    console.print(Panel.fit("[bold green]🚀 TARGETED LIVE TEST: Zylinder Series[/bold green]"))
    
    async with async_session_maker() as session:
        # 1. Purge & Reset
        console.print("🗑️  Cleaning state...")
        await session.exec(delete(Job))
        await session.exec(delete(OrderItem))
        await session.exec(delete(Order))
        
        stmt_real = select(Printer).where(~col(Printer.serial).startswith("SIM"))
        real_printers = (await session.exec(stmt_real)).all()
        for p in real_printers:
            p.current_status = PrinterStatusEnum.IDLE
            p.is_plate_cleared = True
            session.add(p)
        await session.commit()

        # 2. Key SKU Identification
        console.print("\n[bold]Step 2: Identifying Specific SKUs[/bold]")
        # Verified SKUs from database dump:
        specific_targets = ["Zylinder-PLA-FFFFFF", "Zylinder-v2-PLA-FF0000", "Zylinder-v2-PETG-0000FF"]
        found_skus = []
        
        for t_sku in specific_targets:
            stmt = select(ProductSKU).where(ProductSKU.sku == t_sku)
            res = (await session.exec(stmt)).first()
            if res:
                found_skus.append(res.sku)
                console.print(f"✅ Target found: [cyan]{res.name}[/cyan] ({res.sku})")
            else:
                # Try partial match if exact SKU fails
                stmt_alt = select(ProductSKU).where(ProductSKU.sku.ilike(f"%{t_sku}%"))
                res_alt = (await session.exec(stmt_alt)).first()
                if res_alt:
                    found_skus.append(res_alt.sku)
                    console.print(f"✅ Partial match: [cyan]{res_alt.name}[/cyan] ({res_alt.sku})")

        if not found_skus:
            console.print("[red]❌ Error: No specific SKUs found. Aborting.[/red]")
            return

        # 3. Injection
        console.print(f"\n[bold]Step 3: Injecting Order for {len(found_skus)} items[/bold]")
        order_id = await inject_mock_order(session, found_skus)
        console.print(f"📥 Order [bold]{order_id}[/bold] created.")

        # 4. Monitoring
        console.print("\n[bold]Step 4: Monitoring Production (6 min timeout)...[/bold]")
        for i in range(36):
            await session.commit()
            stmt_jobs = select(Job).join(Order).where(Order.ebay_order_id == order_id)
            jobs = (await session.exec(stmt_jobs)).all()
            
            table = Table(title=f"Diagnostic Status (Poll {i+1})")
            table.add_column("Job ID")
            table.add_column("SKU")
            table.add_column("Status")
            
            printing_count = 0
            for j in jobs:
                if j.status == JobStatusEnum.PRINTING: printing_count += 1
                table.add_row(str(j.id), j.gcode_path.split("/")[-1], str(j.status))
            
            console.clear()
            console.print(table)
            
            if printing_count > 0 and printing_count == len(jobs):
                console.print("\n[bold green]✅ ALL JOBS PRINTING (Specific SKU Test PASSED)[/bold green]")
                return
                
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(start_specific_test())
