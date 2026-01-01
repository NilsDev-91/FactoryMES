import asyncio
import os
import sys
from sqlmodel import select, col, update
from rich.console import Console
from rich.panel import Panel

# Add project root
sys.path.append(".")

from app.core.database import async_session_maker
from app.models.core import Printer, PrinterStatusEnum, Job, JobStatusEnum

# Windows AsyncIO Fix
if os.name == 'nt':
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except AttributeError:
        pass

console = Console()

async def force_hardware_sync():
    console.print(Panel.fit("[bold cyan]🔄 Force Hardware Sync: Aligning Digital Twin to Physical Reality[/bold cyan]"))
    
    async with async_session_maker() as session:
        # 1. Identify the Real Printer
        stmt_printer = select(Printer).where(col(Printer.serial).startswith("03919C"))
        real_printers = (await session.exec(stmt_printer)).all()
        
        if not real_printers:
            console.print("[bold red]❌ ERROR: No real printer (03919C...) found in database.[/bold red]")
            return

        for printer in real_printers:
            console.print(f"\n[bold]Synchronizing Printer:[/bold] [cyan]{printer.name}[/cyan] ({printer.serial})")
            console.print(f"   Current DB Status: [yellow]{printer.current_status}[/yellow]")

            # 2. Clear Zombie Jobs
            # Statuses to clear: PRINTING, UPLOADING (as per typical busy states)
            zombie_statuses = [JobStatusEnum.PRINTING, JobStatusEnum.UPLOADING]
            stmt_jobs = select(Job).where(
                col(Job.assigned_printer_serial) == printer.serial,
                col(Job.status).in_(zombie_statuses)
            )
            zombie_jobs = (await session.exec(stmt_jobs)).all()
            
            if zombie_jobs:
                console.print(f"   🕵️  Found {len(zombie_jobs)} zombie jobs. Forcing to FINISHED...")
                for job in zombie_jobs:
                    job.status = JobStatusEnum.FINISHED
                    job.error_message = "Forcefully closed by Hardware Sync (Digital Twin Mismatch)"
                    session.add(job)
                    console.print(f"      ✅ Job {job.id} -> FINISHED")
            else:
                console.print("   ✅ No zombie jobs found.")

            # 3. Reset Printer State
            console.print("   🛠️  Resetting printer state to IDLE...")
            printer.current_status = PrinterStatusEnum.IDLE
            printer.current_job_id = None
            printer.is_plate_cleared = True
            session.add(printer)
            console.print("      ✅ status -> IDLE")
            console.print("      ✅ job_id -> None")
            console.print("      ✅ is_plate_cleared -> True")

        await session.commit()
        console.print("\n[bold green]✨ SUCCESS: Digital Twin is now synchronized with Physical Reality.[/bold green]")
        console.print("The system is now 'Ready for Business'.")

if __name__ == "__main__":
    asyncio.run(force_hardware_sync())
