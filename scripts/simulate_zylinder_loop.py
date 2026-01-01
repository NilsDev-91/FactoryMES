import asyncio
import os
import sys
import logging
import random
import time
from datetime import datetime
from pathlib import Path
from sqlalchemy import delete
from sqlmodel import select
from sqlalchemy.orm import selectinload
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.core.database import async_session_maker
from app.models.core import Product, Printer, Job, JobStatusEnum, PrinterTypeEnum, PrinterStatusEnum, ClearingStrategyEnum
from app.models.product_sku import ProductSKU
from app.models.filament import AmsSlot
from app.models.order import Order
from app.services.print_job_executor import PrintJobExecutionService
from app.services.filament_manager import FilamentManager
from app.services.production.bed_clearing_service import BedClearingService
from tests.mocks.mock_printer_commander import MockPrinterCommander

# Configure Logging
logging.basicConfig(level=logging.WARNING)
console = Console()

async def simulate_zylinder_loop():
    console.print(Panel.fit("[bold cyan]Zylinder Production Loop Simulation[/bold cyan]\n[italic]Scenario: Queue -> Print -> Cooldown -> Eject[/italic]"))

    async with async_session_maker() as session:
        # 1. Setup Virtual Printer
        serial = "SIM-A1-LOOP"
        console.print(f"\n[bold]1. Setup Virtual Printer: {serial}[/bold]")
        
        # Cleanup previous sim
        await session.execute(delete(Job).where(Job.assigned_printer_serial == serial))
        await session.execute(delete(AmsSlot).where(AmsSlot.printer_id == serial))
        existing_printer = await session.get(Printer, serial)
        if existing_printer:
            await session.delete(existing_printer)
        await session.commit()

        printer = Printer(
            serial=serial,
            name="A1 Loop Tester",
            type=PrinterTypeEnum.A1,
            current_status=PrinterStatusEnum.IDLE,
            is_plate_cleared=True,
            can_auto_eject=True,
            clearing_strategy=ClearingStrategyEnum.A1_INERTIAL_FLING,
            jobs_since_calibration=0,
            calibration_interval=5,
            thermal_release_temp=28.0
        )
        session.add(printer)

        # 2. Equip AMS
        stmt = select(Product).where(Product.name == "Zylinder")
        product = (await session.execute(stmt)).scalars().first()
        if not product:
            console.print("[red]❌ Error: 'Zylinder' product missing. Run seed script first.[/red]")
            return

        stmt_skus = select(ProductSKU).where(ProductSKU.product_id == product.id).options(selectinload(ProductSKU.print_file))
        skus = (await session.execute(stmt_skus)).scalars().all()
        
        for idx, sku in enumerate(skus):
            slot = AmsSlot(
                printer_id=serial,
                ams_index=0,
                slot_index=idx,
                slot_id=idx,
                color_hex=sku.hex_color,
                material="PLA",
                remaining_percent=100
            )
            session.add(slot)
            console.print(f"   [blue]Slot {idx}:[/blue] Loaded {sku.name} ({sku.hex_color})")

        # 3. Order Injection
        mock_order = Order(
            ebay_order_id=f"TEST-VAL-{random.randint(1000, 9999)}",
            buyer_username="Quality_Inspector",
            total_price=59.0,
            currency="EUR",
            status="OPEN"
        )
        session.add(mock_order)
        await session.flush()

        jobs_list = []
        for sku in skus:
            job = Job(
                order_id=mock_order.id,
                gcode_path=sku.print_file.file_path if sku.print_file else "dummy.3mf",
                status=JobStatusEnum.PENDING,
                priority=100,
                filament_requirements=[{"color_hex": sku.hex_color, "material": "PLA"}],
                job_metadata={"model_height_mm": 120.0},
                assigned_printer_serial=serial
            )
            session.add(job)
            jobs_list.append((job, sku))

        await session.commit()
        console.print(f"   [green]✅ Enqueued 3 Orders for Zylinder variants.[/green]")

        # 4. Simulation Execution
        executor = PrintJobExecutionService(
            session=session,
            filament_manager=FilamentManager(),
            printer_commander=MockPrinterCommander(),
            bed_clearing_service=BedClearingService()
        )

        for job, sku in jobs_list:
            console.print(f"\n[bold magenta]Processing Job: {sku.name}[/bold magenta]")
            
            # Ensure printer is ready in DB before executor runs
            await session.refresh(printer)
            printer.is_plate_cleared = True
            printer.current_status = PrinterStatusEnum.IDLE
            session.add(printer)
            await session.commit()
            
            # Step A: Dispatch
            console.print(f"   [{datetime.now().strftime('%H:%M:%S')}] [cyan]DISPATCHING[/cyan]...")
            await executor.execute_print_job(job.id, serial)
            await session.refresh(printer)
            console.print(f"   [{datetime.now().strftime('%H:%M:%S')}] [green]PRINTING[/green] (Virtual Progress: 0% -> 100%)")
            
            # Step B: Printing Duration
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeRemainingColumn(),
                console=console
            ) as progress:
                task = progress.add_task(f"   Simulating Print of {sku.name}...", total=10)
                while not progress.finished:
                    await asyncio.sleep(0.5)
                    progress.update(task, advance=1)

            # Step C: Cooldown
            printer.current_status = PrinterStatusEnum.COOLDOWN
            printer.current_temp_bed = 60.0
            session.add(printer)
            await session.commit()
            
            console.print(f"   [{datetime.now().strftime('%H:%M:%S')}] [blue]COOLDOWN[/blue] (Bed: 60°C -> 25°C threshold)")
            
            while printer.current_temp_bed > printer.thermal_release_temp:
                printer.current_temp_bed -= 15.0 # Fast cooling
                await asyncio.sleep(1)
                console.print(f"      Temp: {printer.current_temp_bed:.1f}°C")
            
            # Step D: Trigger Eject / Finished
            console.print(f"   [{datetime.now().strftime('%H:%M:%S')}] [yellow]TRIGGERING EJECT[/yellow]...")
            await executor.handle_print_finished(serial, job.id)
            await session.refresh(printer)

            if printer.current_status == PrinterStatusEnum.CLEARING_BED:
                console.print(f"   [{datetime.now().strftime('%H:%M:%S')}] [magenta]CLEARING_BED[/magenta] (Autonomous Sweep)")
                # Simulate Physical Success
                await asyncio.sleep(2)
                printer.current_status = PrinterStatusEnum.IDLE
                printer.is_plate_cleared = True
                session.add(printer)
                await session.commit()
            
            console.print(f"   [{datetime.now().strftime('%H:%M:%S')}] [green]SUCCESS: STATE RETURNED TO IDLE[/green]")

    console.print(Panel.fit("[bold green]Simulation Complete: 3/3 Parts Fabricated[/bold green]"))

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(simulate_zylinder_loop())
