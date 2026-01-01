import asyncio
import os
import sys
import logging
from sqlmodel import select, delete, col
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Add project root
sys.path.append(".")

from app.core.database import async_session_maker
from app.models.core import Printer, Job, JobStatusEnum
from app.models.order import Order, OrderItem
from app.models.filament import AmsSlot

# Setup
console = Console()
logging.basicConfig(level=logging.ERROR)

REAL_PRINTER_SERIAL = "03919C461802608"

async def fix_and_verify():
    console.print(Panel.fit("[bold green]🔧 FINAL SYSTEM AUDIT & KICKSTART[/bold green]"))

    async with async_session_maker() as session:
        # 1. Audit & Cleanup Printers
        console.print("\n[bold]Phase 1: Hardware Audit[/bold]")
        stmt_printers = select(Printer)
        all_printers = (await session.exec(stmt_printers)).all()
        
        ghost_printers = [p for p in all_printers if p.serial != REAL_PRINTER_SERIAL]
        
        if ghost_printers:
            console.print(f"⚠️  Found {len(ghost_printers)} ghost printers. Purging...")
            ghost_serials = [p.serial for p in ghost_printers]
            
            # Clean dependencies
            await session.exec(delete(AmsSlot).where(col(AmsSlot.printer_id).in_(ghost_serials)))
            await session.exec(delete(Printer).where(col(Printer.serial).in_(ghost_serials)))
            await session.commit()
            console.print(f"   🗑️  Deleted: {', '.join(ghost_serials)}")
        else:
            console.print("✅ No ghost printers found.")

        # 2. Audit & Cleanup Orders
        console.print("\n[bold]Phase 2: Order Audit[/bold]")
        stmt_orders = select(Order).order_by(col(Order.id).desc())
        all_orders = (await session.exec(stmt_orders)).all()
        
        if len(all_orders) > 1:
            main_order = all_orders[0]
            ghost_orders = all_orders[1:]
            console.print(f"⚠️  Found {len(ghost_orders)} old/ghost orders. Keeping newest: {main_order.ebay_order_id}")
            
            ghost_ids = [o.id for o in ghost_orders]
            
            # Delete dependencies
            await session.exec(delete(Job).where(col(Job.order_id).in_(ghost_ids)))
            await session.exec(delete(OrderItem).where(col(OrderItem.order_id).in_(ghost_ids)))
            await session.exec(delete(Order).where(col(Order.id).in_(ghost_ids)))
            await session.commit()
            console.print(f"   🗑️  Deleted {len(ghost_ids)} ghost orders.")
        elif len(all_orders) == 1:
            console.print(f"✅ Healthy order state: 1 active order ({all_orders[0].ebay_order_id})")
        else:
            console.print("❓ No orders found.")

        # 3. Display Final State
        console.print("\n[bold]Phase 3: Current State Table[/bold]")
        table = Table(title="System Single Source of Truth")
        table.add_column("Type", style="cyan")
        table.add_column("Identifier", style="magenta")
        table.add_column("Status/Details", style="green")

        # Refetch 
        db_printer = await session.get(Printer, REAL_PRINTER_SERIAL)
        if db_printer:
            table.add_row("Printer", db_printer.serial, f"{db_printer.name} ({db_printer.current_status})")
        
        latest_order = (await session.exec(select(Order).order_by(col(Order.id).desc()))).first()
        if latest_order:
            table.add_row("Order", latest_order.ebay_order_id, latest_order.status)
            
        latest_job = (await session.exec(select(Job).order_by(col(Job.id).desc()))).first()
        if latest_job:
            table.add_row("Job", str(latest_job.id), latest_job.status)

        console.print(table)

        # 4. FMS Kickstart (Override)
        console.print("\n[bold]Phase 4: FMS Kickstart (Override)[/bold]")
        if latest_job and latest_job.status == JobStatusEnum.PENDING:
            reqs = latest_job.filament_requirements
            if isinstance(reqs, list) and len(reqs) > 0:
                target_color = reqs[0].get("color") or reqs[0].get("hex_color")
                target_material = reqs[0].get("material", "PLA")
                
                console.print(f"🚀 Aligning Printer {REAL_PRINTER_SERIAL} Slot 1 to {target_color} ({target_material})")
                
                # Check for Slot 1
                stmt_slot = select(AmsSlot).where(AmsSlot.printer_id == REAL_PRINTER_SERIAL, AmsSlot.slot_id == 0)
                slot = (await session.exec(stmt_slot)).first()
                if not slot:
                    slot = AmsSlot(printer_id=REAL_PRINTER_SERIAL, ams_index=0, slot_index=0, slot_id=0)
                    session.add(slot)
                
                slot.color_hex = target_color
                slot.material = target_material
                slot.remaining_percent = 100
                
                # Force Printer state
                db_printer.current_status = "IDLE"
                db_printer.is_plate_cleared = True
                
                session.add(slot)
                session.add(db_printer)
                await session.commit()
                console.print("✨ [bold green]Kickstart Successful![/bold green] Database is now aligned. FleetManager should pick up the job momentarily.")
            else:
                console.print("⚠️  Job filament requirements invalid. Cannot kickstart.")
        else:
            console.print("ℹ️  No pending job found to kickstart.")

    console.print(f"\n[bold green]System Audit Complete.[/bold green]\n")

if __name__ == "__main__":
    if os.name == 'nt':
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except AttributeError:
            pass
    asyncio.run(fix_and_verify())
