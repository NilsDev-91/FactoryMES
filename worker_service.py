
import asyncio
import logging
import sys
from datetime import datetime
from typing import Dict, Any

from sqlmodel import select, col
from database import async_session_maker
from models import Printer, Job, JobStatusEnum, PrinterStatusEnum, Order, OrderStatusEnum, Product
from bambu_client import BambuPrinterClient

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("WorkerService")

# Global State Cache
# Structure: { serial: { "current_status": ..., "current_temp_nozzle": ..., ... } }
PRINTER_STATE_CACHE: Dict[str, Dict[str, Any]] = {}

def handle_mqtt_update(serial: str, data: Dict[str, Any]):
    """
    Updates the in-memory cache with new telemetry data from MQTT.
    Does NOT write to DB.
    """
    if serial not in PRINTER_STATE_CACHE:
        PRINTER_STATE_CACHE[serial] = {}
    
    PRINTER_STATE_CACHE[serial].update(data)
    # logger.debug(f"Updated cache for {serial}: {data}")

async def sync_loop():
    """
    Background task that runs every 5 seconds.
    1. Syncs cached state to DB.
    2. Assigns PENDING jobs to IDLE printers.
    """
    logger.info("Starting Sync Loop...")
    while True:
        try:
            async with async_session_maker() as session:
                # --- STEP 1: Sync Cache to DB ---
                if PRINTER_STATE_CACHE:
                    # We iterate over a copy of keys to avoid modification issues if needed, 
                    # though python dict keys iteration is usually safe if we don't add keys.
                    for serial, data in PRINTER_STATE_CACHE.items():
                        printer = await session.get(Printer, serial)
                        if printer:
                            data_changed = False
                            
                            # Update fields if present in data
                            if "print_status" in data:
                                # Map 'print_status' string to Enum if possible
                                # Assuming data["print_status"] matches raw strings like "IDLE", "RUNNING"
                                # We might need normalization. 
                                # For now, direct assignment if it matches Enum, else fallback or ignore?
                                # Let's assume the raw string is close enough or use a mapper.
                                # Simple mapping:
                                raw_status = data["print_status"]
                                if raw_status in ["IDLE", "FINISH"]:
                                    printer.current_status = PrinterStatusEnum.IDLE
                                elif raw_status == "RUNNING":
                                    printer.current_status = PrinterStatusEnum.PRINTING
                                else:
                                    # Keep as is or map to IDLE/PRINTING based on context
                                    pass 
                                data_changed = True

                            if "nozzle_temper" in data:
                                printer.current_temp_nozzle = float(data["nozzle_temper"])
                                data_changed = True
                            
                            if "bed_temper" in data:
                                printer.current_temp_bed = float(data["bed_temper"])
                                data_changed = True
                            
                            if data_changed:
                                session.add(printer)
                    
                    await session.commit()
                
                # --- STEP 2: Job Matching ---
                # Find IDLE printers
                result = await session.execute(
                    select(Printer).where(Printer.current_status == PrinterStatusEnum.IDLE)
                )
                idle_printers = result.scalars().all()
                
                if idle_printers:
                    # Check for waiting Jobs
                    result = await session.execute(
                        select(Job)
                        .where(Job.status == JobStatusEnum.PENDING)
                        .order_by(Job.created_at.asc())
                    )
                    pending_jobs = result.scalars().all()
                    
                    for job in pending_jobs:
                        if not idle_printers:
                            break
                        
                        # Get Order to find SKU -> Product Requirements
                        order = await session.get(Order, job.order_id)
                        if not order:
                            logger.error(f"Job {job.id} has invalid order {job.order_id}")
                            continue

                        # Find Product by SKU
                        result = await session.execute(select(Product).where(Product.sku == order.sku))
                        product = result.scalars().first()
                        
                        # Find a compatible printer among idle ones
                        compatible_printer = None
                        
                        # If no product found, we can't check requirements. 
                        # DECISION: Fail safe? Or unsafe? Let's assume unsafe and require product.
                        if not product:
                             logger.warning(f"Order {order.id} SKU {order.sku} not found in Products table. Cannot verify materials.")
                             # Skip or fail? Skipping for now.
                             continue

                        for p in idle_printers:
                            if check_material_match(p, product):
                                compatible_printer = p
                                break
                        
                        if compatible_printer:
                            # Assign
                            logger.info(f"Assigning Job {job.id} (Order {job.order_id}) to Printer {compatible_printer.serial} ({compatible_printer.name})")
                            
                            job.assigned_printer_serial = compatible_printer.serial
                            job.status = JobStatusEnum.PRINTING
                            
                            compatible_printer.current_status = PrinterStatusEnum.PRINTING
                            
                            session.add(job)
                            session.add(compatible_printer)
                            
                            # Remove from available pool for this loop
                            idle_printers.remove(compatible_printer)
                            
                            logger.info(f"COMMAND: Start Printing {job.gcode_path} on {compatible_printer.serial}")
                        else:
                            logger.debug(f"No compatible printer found for Job {job.id} (Req: {product.required_filament_type} {product.required_filament_color})")

                    if pending_jobs:
                        await session.commit()

        except Exception as e:
            logger.error(f"Error in sync_loop: {e}", exc_info=True)
        
        await asyncio.sleep(5)

def check_material_match(printer: Printer, product: Product) -> bool:
    """
    Checks if the printer has the required filament loaded in AMS.
    Robust Logic: Strict Type match, Empty Check, Color Logic.
    """
    req_type = product.required_filament_type
    req_color = product.required_filament_color

    if not req_type:
        return True # No requirements

    if not printer.ams_data:
        # No AMS data means we can't verify. Safe fallback is False.
        return False

    ams_slots = printer.ams_data # SQLModel/Postgres handles JSON decoding

    for slot in ams_slots:
        # Check standard format
        if not isinstance(slot, dict):
            continue
            
        slot_type = slot.get('type', 'UNKNOWN')
        slot_color = slot.get('color', None)
        remaining = slot.get('remaining', 0)

        # 1. Empty Spool Check
        if remaining <= 0:
            continue

        # 2. Type Check (Strict, Case Insensitive)
        # We use strict equality to avoid "Support for PLA" matching "PLA"
        if req_type.lower() != slot_type.lower():
            continue
        
        # 3. Color Check 
        if req_color:
            if not slot_color:
                continue
            # Simple exact match (case insensitive)
            if req_color.lower() != slot_color.lower():
                continue

        # If we passed all checks, it's a match
        return True

    return False

async def main():
    logger.info("Initializing Worker Service...")
    
    # 1. Load Printers from DB
    clients = []
    async with async_session_maker() as session:
        result = await session.execute(select(Printer))
        printers = result.scalars().all()
        
        if not printers:
            logger.warning("No printers found in database. Please run init_db.py or add printers.")
        
        for p in printers:
            if p.ip_address and p.access_code:
                logger.info(f"Starting client for {p.name} ({p.serial}) at {p.ip_address}")
                
                # Create callback with bound serial
                def callback(data, serial=p.serial):
                    handle_mqtt_update(serial, data)
                
                client = BambuPrinterClient(
                    ip=p.ip_address,
                    access_code=p.access_code,
                    serial=p.serial,
                    update_callback=callback
                )
                
                # Check for Windows Event Loop Policy inside BambuClient or here?
                # It's better to ensure policy is set at entry point (if __name__ == main)
                
                asyncio.create_task(client.connect_mqtt())
                clients.append(client)
    
    # 2. Start Sync Loop
    asyncio.create_task(sync_loop())
    
    # 3. Keep Alive
    logger.info("Worker Service Running. Press Ctrl+C to stop.")
    try:
        # Wait forever
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("Shutting down...")
        for c in clients:
            c.stop()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
