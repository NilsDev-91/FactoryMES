
import asyncio
import json
import logging
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.database import engine
from app.models.core import Printer, PrinterStatusEnum, ClearingStrategyEnum, PrinterTypeEnum
from app.services.printer.mqtt_worker import PrinterMqttWorker

"""
Phase 8: Chaos Engineering - "War Games"
Final Injection Script: Verifies HMS -> Worker -> DB logic.
"""

# Configure logging for better visibility
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ChaosSimulator")

SERIAL = "sim_printer_01"

async def ensure_printer_exists():
    """Ensure the simulation printer exists in the DB."""
    async with AsyncSession(engine) as session:
        statement = select(Printer).where(Printer.serial == SERIAL)
        results = await session.execute(statement)
        printer = results.scalar_one_or_none()
        
        if not printer:
            print(f"[*] Creating {SERIAL} in Database...")
            printer = Printer(
                serial=SERIAL,
                name="Chaos Simulator",
                type=PrinterTypeEnum.A1,
                current_status=PrinterStatusEnum.IDLE,
                clearing_strategy=ClearingStrategyEnum.A1_INERTIAL_FLING
            )
            session.add(printer)
        else:
            print(f"[*] Resetting {SERIAL} status to IDLE...")
            printer.current_status = PrinterStatusEnum.IDLE
            printer.last_error_code = None
            printer.last_error_description = None
            session.add(printer)
        
        await session.commit()

async def update_db_status(status: PrinterStatusEnum):
    """Update printer status in DB."""
    async with AsyncSession(engine) as session:
        statement = select(Printer).where(Printer.serial == SERIAL)
        results = await session.execute(statement)
        printer = results.scalar_one_or_none()
        if printer:
            printer.current_status = status
            session.add(printer)
            await session.commit()
            print(f"[DB] Pre-Condition set: {status.value}")

async def get_db_state():
    """Fetch current printer status and error code from DB."""
    async with AsyncSession(engine) as session:
        statement = select(Printer).where(Printer.serial == SERIAL)
        results = await session.execute(statement)
        printer = results.scalar_one_or_none()
        return (printer.current_status.value, printer.last_error_code) if printer else ("UNKNOWN", None)

async def run_war_games():
    print("=== Phase 8: Chaos Injection Tool (War Games) ===")
    
    # 0. Setup
    await ensure_printer_exists()
    worker = PrinterMqttWorker()
    
    # --- Scenario A: AMS Feed Fail (Warning/Pause) ---
    print("\n[Scenario A] The Stuck Plunger (Filament Runout)")
    await update_db_status(PrinterStatusEnum.PRINTING)
    
    # Mock HMS Payload
    payload = {
        "print": {
            "hms": [{"code": "0700-2000-0002-0002"}],
            "gcode_state": "RUNNING"
        }
    }
    
    print("[*] Injecting AMS Failure...")
    await worker._handle_message(SERIAL, payload)
    
    status, error = await get_db_state()
    if status == "PAUSED" and error == "0700-2000-0002-0002":
        print(f"[SUCCESS] PRINTING -> {status} confirmed. Error: {error}")
    else:
        print(f"[FAILURE] Expected PAUSED, got {status} (Error: {error})")

    # --- Scenario B: The Crash (Gantry Stall) ---
    print("\n[Scenario B] The Gantry Crash (Axis Stall)")
    await update_db_status(PrinterStatusEnum.CLEARING_BED)
    
    # Mock HMS Payload
    payload = {
        "print": {
            "hms": [{"code": "0300-0100-0001-0001"}],
            "print_error": 117440512,
            "gcode_state": "RUNNING"
        }
    }
    
    print("[*] Injecting Motor Stall Failure...")
    await worker._handle_message(SERIAL, payload)
    
    status, error = await get_db_state()
    if status == "ERROR" and error == "0300-0100-0001-0001":
        print(f"[SUCCESS] CLEARING_BED -> {status} confirmed. Error: {error}")
    else:
        print(f"[FAILURE] Expected ERROR, got {status} (Error: {error})")

    print("\n=== War Games Complete ===")

if __name__ == "__main__":
    asyncio.run(run_war_games())
