import asyncio
import os
import sys
import logging
from pathlib import Path
from sqlalchemy.orm import selectinload
from sqlmodel import select
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import async_session_maker
from app.models.core import Product, Printer, PrinterTypeEnum, PrinterStatusEnum
from app.models.product_sku import ProductSKU
from app.models.print_file import PrintFile
from app.models.filament import AmsSlot
from app.services.filament_manager import FilamentManager

console = Console()

async def verify_zylinder_state():
    console.print(Panel.fit("[bold cyan]Zylinder System Diagnostic Audit[/bold cyan]"))
    
    async with async_session_maker() as session:
        # 1. Product Existence
        console.print("\n[bold]1. Database Product Search[/bold]")
        stmt = select(Product).where(Product.name == "Zylinder")
        product = (await session.execute(stmt)).scalars().first()
        
        if not product:
            console.print("[red]❌ CRITICAL ERROR: Product 'Zylinder' not found in database.[/red]")
            sys.exit(1)
        console.print(f"[green]✅ Product Found:[/green] {product.name} (ID: {product.id})")

        # 2. Variant Audit
        console.print("\n[bold]2. SKU & Color Forensic Audit[/bold]")
        stmt = select(ProductSKU).where(ProductSKU.product_id == product.id).options(selectinload(ProductSKU.print_file))
        skus = (await session.execute(stmt)).scalars().all()
        
        table = Table(title="SKU Inventory Audit")
        table.add_column("SKU Name", style="cyan")
        table.add_column("SKU Code", style="magenta")
        table.add_column("Hex Color", style="yellow")
        table.add_column("File Link", style="blue")
        table.add_column("Disk Status", justify="center")

        for sku in skus:
            # File Check
            file_status = "[red]MISSING[/red]"
            if sku.print_file and Path(sku.print_file.file_path).exists():
                file_status = "[green]EXISTS[/green]"
            
            link_status = "[green]OK[/green]" if sku.print_file_id else "[red]NULL[/red]"
            
            table.add_row(
                sku.name,
                sku.sku,
                sku.hex_color or "N/A",
                link_status,
                file_status
            )

        console.print(table)
        
        if len(skus) != 3:
            console.print(f"[red]❌ Audit Failed: Expected 3 SKUs, found {len(skus)}.[/red]")
            sys.exit(1)

        # 3. FMS Dry Run
        console.print("\n[bold]3. FMS Dispatch Logic (Dry Run)[/bold]")
        
        red_sku = next((s for s in skus if "ROT" in s.name.upper() or "RED" in s.name.upper()), None)
        if not red_sku:
             console.print("[yellow]⚠️ Skipping FMS dry run: No 'Red' variant identified.[/yellow]")
        else:
            fms = FilamentManager()
            
            # Virtual Red Inventory
            mock_printer = Printer(serial="VIRTUAL_AUDIT", name="Audit-Twin", type=PrinterTypeEnum.A1)
            mock_slot = AmsSlot(
                printer_id="VIRTUAL_AUDIT",
                ams_index=0,
                slot_index=0,
                color_hex="#FF0000", # Pure Red
                material="PLA"
            )
            mock_printer.ams_slots = [mock_slot]
            
            from app.models.core import Job
            mock_job = Job(
                order_id=0,
                gcode_path=red_sku.print_file.file_path if red_sku.print_file else "",
                filament_requirements=[{"color_hex": red_sku.hex_color, "material": "PLA"}]
            )
            
            match = fms.can_printer_print_job(mock_printer, mock_job)
            
            if match:
                console.print(f"[green]✅ FMS Matching Logic: Passive Confirmation Success for '{red_sku.name}'.[/green]")
            else:
                console.print(f"[red]❌ FMS Matching Logic: Match FAILED for '{red_sku.name}' against #FF0000.[/red]")
                sys.exit(1)

    console.print(f"\n[bold green]✨ Forensic State Audit: CLEAN[/bold green]\n")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(verify_zylinder_state())
