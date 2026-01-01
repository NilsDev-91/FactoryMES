"""
Phase 5 Simulation: Smart A1 Automation (Physics & Logic)

Proves the entire autonomous stack:
- State Machine
- Material Guard (FilamentMismatchError)
- Smart Gantry Sweep
- Dynamic Calibration Optimization

Scenario:
- Printer: Virtual A1, Calibration Interval=2
- Job 1 (Red): jobs_since_cal=0 -> Full Calibration + Sweep -> jobs_since_cal=1
- Job 2 (Red): jobs_since_cal=1 -> Optimized Start (No G29) + Sweep -> jobs_since_cal=2
- Job 3 (Blue): Material Guard Block (No matching slot)
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path BEFORE any app imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, delete

from app.core.database import async_session_maker
from app.core.exceptions import FilamentMismatchError
from app.models.core import Printer, Job, JobStatusEnum, PrinterTypeEnum, PrinterStatusEnum, ClearingStrategyEnum
from app.models.filament import AmsSlot
from app.models.order import Order
from app.services.print_job_executor import PrintJobExecutionService
from app.services.filament_manager import FilamentManager
from app.services.production.bed_clearing_service import BedClearingService

# Import Mock Commander
from tests.mocks.mock_printer_commander import MockPrinterCommander

# Configure Logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("InfiniteLoopSim")
logger.setLevel(logging.INFO)

# Silence noisy loggers for cleaner output
logging.getLogger("MockPrinterCommander").setLevel(logging.DEBUG)
logging.getLogger("PrintJobExecutionService").setLevel(logging.WARNING)
logging.getLogger("FilamentManager").setLevel(logging.WARNING)


def print_banner():
    """Print the simulation banner."""
    print(r"""
   ___       _   _       _ _        _                   
  / _ \     | | (_)     (_) |      | |                  
 / /_\ \_ __| |_ _  __ _ _| |_ __ _| | ____ _ _ __ _ __ 
 |  _  | '_ \ __| |/ _` | | __/ _` | |/ / _` | '__| '__|
 | | | | | | | |_| | (_| | | || (_| |   < (_| |  |  |  
 \_| |_/_| |_|\__|_|\__, |_|\__\__,_|_|\_\__,_|_|  |_|  
                     __/ |                              
                    |___/                               
    """)
    print("=" * 60)
    print("  PHASE 5: Smart A1 Automation (Physics & Logic)")
    print("  Simulation Mode - No Hardware Communication")
    print("=" * 60)


def print_timeline(timeline: list):
    """Print a formatted ASCII timeline."""
    print("\n" + "=" * 70)
    print(" EXECUTION TIMELINE")
    print("=" * 70)
    print("┌─────────────┬────────────────┬────────────┬─────────────────────────┐")
    print("│ Time        │ Job            │ Status     │ Optimization Event      │")
    print("├─────────────┼────────────────┼────────────┼─────────────────────────┤")
    
    for entry in timeline:
        time_str = entry.get("time", "")[:12].ljust(11)
        job_str = entry.get("job", "")[:14].ljust(14)
        status_str = entry.get("status", "")[:10].ljust(10)
        note_str = entry.get("note", "")[:23].ljust(23)
        print(f"│ {time_str} │ {job_str} │ {status_str} │ {note_str} │")
    
    print("└─────────────┴────────────────┴────────────┴─────────────────────────┘")


async def simulate():
    print_banner()
    
    async with async_session_maker() as session:
        # =========================================
        # 1. Setup Virtual Printer
        # =========================================
        serial = "VIRTUAL_A1_SIM"
        logger.info(f"Creating Virtual Printer: {serial} (Calibration Interval=2)")
        
        # Cleanup previous simulation data
        await session.exec(delete(Job).where(Job.assigned_printer_serial == serial))
        await session.exec(delete(AmsSlot).where(AmsSlot.printer_id == serial))
        existing_printer = await session.get(Printer, serial)
        if existing_printer:
            await session.delete(existing_printer)
        await session.commit()
        
        # Ensure Dummy Order for FK constraint
        mock_order_id = 9999
        mock_order = await session.get(Order, mock_order_id)
        if not mock_order:
            mock_order = Order(
                id=mock_order_id,
                ebay_order_id="MOCK_PHASE5_SIM",
                buyer_username="simulation_user",
                total_price=0.0,
                currency="USD",
                status="MOCK"
            )
            session.add(mock_order)
            await session.commit()

        # Create A1 Printer with Phase 5 config
        printer = Printer(
            serial=serial,
            name="Virtual A1 - Phase 5 Test",
            ip_address="127.0.0.1",
            access_code="SIMTEST1",
            type=PrinterTypeEnum.A1,
            current_status=PrinterStatusEnum.IDLE,
            is_plate_cleared=True,
            can_auto_eject=True,
            clearing_strategy=ClearingStrategyEnum.A1_INERTIAL_FLING,
            jobs_since_calibration=0,  # Fresh start
            calibration_interval=2,    # Calibrate every 2 jobs
            thermal_release_temp=28.0
        )
        session.add(printer)
        await session.commit()
        await session.refresh(printer)
        
        print(f"\n✓ Printer Created: {printer.name}")
        print(f"  - Calibration Interval: {printer.calibration_interval}")
        print(f"  - Jobs Since Calibration: {printer.jobs_since_calibration}")

        # =========================================
        # 2. Setup AMS Slots (Filament Inventory)
        # =========================================
        slots = [
            AmsSlot(printer_id=serial, ams_index=0, slot_index=0, 
                    tray_color="#FF0000", tray_type="PLA", remaining_percent=100),  # RED
            AmsSlot(printer_id=serial, ams_index=0, slot_index=1, 
                    tray_color="#00FF00", tray_type="PLA", remaining_percent=100),  # GREEN
            AmsSlot(printer_id=serial, ams_index=0, slot_index=2, 
                    tray_color="#00FFFF", tray_type="PLA", remaining_percent=100),  # CYAN (Not Blue!)
            AmsSlot(printer_id=serial, ams_index=0, slot_index=3, 
                    tray_color="#FFFF00", tray_type="PLA", remaining_percent=100),  # YELLOW
        ]
        for s in slots:
            session.add(s)
        await session.commit()
        await session.refresh(printer)
        
        print(f"✓ AMS Inventory Loaded:")
        for s in slots:
            print(f"  - Slot {s.slot_index}: {s.tray_color} ({s.tray_type})")

        # =========================================
        # 3. Create Test Jobs
        # =========================================
        # Create dummy 3MF file for simulation
        import os
        import zipfile
        
        dummy_dir = Path("temp/simulation")
        dummy_dir.mkdir(parents=True, exist_ok=True)
        dummy_gcode = dummy_dir / "phase5_test.3mf"
        
        with zipfile.ZipFile(dummy_gcode, 'w') as z:
            z.writestr("Metadata/plate_1.gcode", 
                       "; Dummy G-code\nG28\nG29 ; Bed Leveling\nM968 ; Flow Dynamics\nG1 X10 Y10")
            z.writestr("Metadata/model_settings.config", "")
            z.writestr("Metadata/slice_info.config", 
                       "<config><plate><filament id='1' type='PLA' color='#FFFFFF'/></plate></config>")
        
        # Job 1: RED - Should MATCH (Slot 0)
        job1 = Job(
            order_id=mock_order_id,
            gcode_path=str(dummy_gcode),
            status=JobStatusEnum.PENDING,
            priority=100,
            filament_requirements=[{"color_hex": "#FF0000", "material": "PLA"}],
            job_metadata={"model_height_mm": 75.0},  # > 50mm, safe for sweep
            assigned_printer_serial=serial
        )
        
        # Job 2: RED - Should MATCH (Slot 0)
        job2 = Job(
            order_id=mock_order_id,
            gcode_path=str(dummy_gcode),
            status=JobStatusEnum.PENDING,
            priority=90,
            filament_requirements=[{"color_hex": "#FF0000", "material": "PLA"}],
            job_metadata={"model_height_mm": 120.0},  # Tall part
            assigned_printer_serial=serial
        )
        
        # Job 3: BLUE (#0000FF) - Should BLOCK (No match, Cyan #00FFFF is Delta E > 5)
        job3 = Job(
            order_id=mock_order_id,
            gcode_path=str(dummy_gcode),
            status=JobStatusEnum.PENDING,
            priority=80,
            filament_requirements=[{"color_hex": "#0000FF", "material": "PLA"}],  # BLUE
            job_metadata={"model_height_mm": 60.0},
            assigned_printer_serial=serial
        )
        
        session.add(job1)
        session.add(job2)
        session.add(job3)
        await session.commit()
        
        print(f"\n✓ Jobs Queued:")
        print(f"  - Job {job1.id}: RED (#FF0000), Height: 75mm, Priority: 100")
        print(f"  - Job {job2.id}: RED (#FF0000), Height: 120mm, Priority: 90")
        print(f"  - Job {job3.id}: BLUE (#0000FF), Height: 60mm, Priority: 80")

        # =========================================
        # 4. Initialize Executor with MOCK Commander
        # =========================================
        mock_commander = MockPrinterCommander()
        
        executor = PrintJobExecutionService(
            session=session,
            filament_manager=FilamentManager(),
            printer_commander=mock_commander,  # USE MOCK!
            bed_clearing_service=BedClearingService()
        )
        
        print(f"\n✓ Executor Initialized with MockPrinterCommander")

        # =========================================
        # 5. Execution Loop
        # =========================================
        timeline = []
        
        async def run_job_cycle(job: Job, job_name: str):
            """Execute a single job cycle and record results."""
            try:
                # Refresh printer state
                await session.refresh(printer)
                
                start_cal = printer.jobs_since_calibration
                is_cal_due = (start_cal >= printer.calibration_interval) or (start_cal == 0)
                
                print(f"\n{'='*50}")
                print(f"  Processing: {job_name} (ID: {job.id})")
                print(f"  Calibration Counter: {start_cal}/{printer.calibration_interval}")
                print(f"  Calibration Due: {is_cal_due}")
                print(f"{'='*50}")
                
                # Execute the job
                await executor.execute_print_job(job.id, serial)
                
                # Refresh job to check status
                await session.refresh(job)
                
                if job.status != JobStatusEnum.PRINTING:
                    raise Exception(f"Unexpected status: {job.status}, Error: {job.error_message}")
                
                # Simulate print completion
                print(f"  [SIM] Print running... (simulating completion)")
                await executor.handle_print_finished(serial, job.id)
                
                # Refresh for post-state
                await session.refresh(printer)
                end_cal = printer.jobs_since_calibration
                
                # Determine optimization event
                if is_cal_due:
                    opt_event = "CALIBRATED"
                else:
                    opt_event = "OPTIMIZED (Skip G29)"
                
                timeline.append({
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "job": job_name,
                    "status": "SUCCESS",
                    "note": f"Cal: {start_cal}→{end_cal} ({opt_event})"
                })
                
                print(f"  ✓ Job Complete. Counter: {start_cal} → {end_cal}")
                
                # CRITICAL: Reset plate for next job (simulation only)
                printer.is_plate_cleared = True
                printer.current_status = PrinterStatusEnum.IDLE
                session.add(printer)
                await session.commit()
                
            except FilamentMismatchError as e:
                timeline.append({
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "job": job_name,
                    "status": "BLOCKED",
                    "note": "FilamentMismatchError"
                })
                print(f"  ✗ Material Guard BLOCKED: {e.detail}")
                
            except Exception as e:
                timeline.append({
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "job": job_name,
                    "status": "ERROR",
                    "note": str(e)[:23]
                })
                print(f"  ✗ Error: {e}")

        # Run all jobs
        await run_job_cycle(job1, "Job 1 (Red)")
        await run_job_cycle(job2, "Job 2 (Red)")
        await run_job_cycle(job3, "Job 3 (Blue)")

        # =========================================
        # 6. Print Results
        # =========================================
        print_timeline(timeline)
        
        # Final State
        await session.refresh(printer)
        print(f"\n FINAL STATE")
        print(f"{'─'*40}")
        print(f"  Printer Status: {printer.current_status.value}")
        print(f"  Jobs Since Calibration: {printer.jobs_since_calibration}")
        print(f"  Plate Cleared: {printer.is_plate_cleared}")
        
        # Commander Summary
        summary = mock_commander.get_summary()
        print(f"\n MOCK COMMANDER SUMMARY")
        print(f"{'─'*40}")
        print(f"  Jobs Started: {summary['total_starts']}")
        for start in summary['starts']:
            cal_mode = "CALIBRATED" if start['is_calibration_due'] else "OPTIMIZED"
            print(f"    - Job {start['job_id']}: {cal_mode}")

        # Cleanup
        if dummy_gcode.exists():
            dummy_gcode.unlink()


if __name__ == "__main__":
    asyncio.run(simulate())
