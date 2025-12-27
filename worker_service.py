
import asyncio
import logging
import sys
import os
import zipfile
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
logger.setLevel(logging.INFO)
logging.getLogger("BambuClient").setLevel(logging.INFO) # Enable telemetry for debugging


# Global State Cache
# Structure: { serial: { "current_status": ..., "current_temp_nozzle": ..., ... } }
PRINTER_STATE_CACHE: Dict[str, Dict[str, Any]] = {}

# Global Client Registry
# Structure: { serial: BambuPrinterClient }
PRINTER_CLIENTS: Dict[str, BambuPrinterClient] = {}

async def execute_print_job(client: BambuPrinterClient, job_id: int, local_path: str, ams_mapping: list = None):
    """
    Uploads file and starts print. 
    Handles errors by updating Job status to FAILED and freeing the Printer.
    """
    logger.info(f"JOB {job_id}: Executing Print Job on {client.serial}...")
    
    try:
        filename = os.path.basename(local_path)
        target_path = f"/{filename}"

        logger.info(f"JOB {job_id}: Starting Upload of {local_path} to {target_path}...")
        
        # Upload
        await client.upload_file(local_path, target_path)
        logger.info(f"JOB {job_id}: Upload Complete.")

        # Determine internal G-code path
        internal_gcode_path = "Metadata/plate_1.gcode"
        try:
            with zipfile.ZipFile(local_path, 'r') as z:
                for name in z.namelist():
                    if name.startswith("Metadata/") and name.endswith(".gcode") and not name.endswith(".md5"):
                        internal_gcode_path = name
                        logger.info(f"JOB {job_id}: Found internal G-code path: {name}")
                        break
        except Exception as zip_err:
             logger.warning(f"JOB {job_id}: Failed to inspect 3MF zip structure: {zip_err}. Using default: {internal_gcode_path}")

        # Start Print
        logger.info(f"JOB {job_id}: Sending Print Command with Mapping {ams_mapping} using param {internal_gcode_path}...")
        await client.start_print(target_path, ams_mapping=ams_mapping, gcode_internal_path=internal_gcode_path)
        logger.info(f"JOB {job_id}: Print Command Sent!")

        # Update Job Status to PRINTING (Exit UPLOADING state)
        async with async_session_maker() as session:
             job = await session.get(Job, job_id)
             if job:
                 job.status = JobStatusEnum.PRINTING
                 session.add(job)
                 await session.commit()
                 logger.info(f"JOB {job_id}: Status updated to PRINTING")

    except Exception as e:
        logger.error(f"JOB {job_id}: FAILED - {e}")
        
        # Update DB State on Failure
        try:
            async with async_session_maker() as session:
                # Get Job
                job = await session.get(Job, job_id)
                if job:
                    job.status = JobStatusEnum.FAILED
                    job.error_message = str(e)
                    session.add(job)
                    
                    # Also Update Order to FAILED
                    order = await session.get(Order, job.order_id)
                    if order:
                        order.status = OrderStatusEnum.FAILED
                        order.error_message = str(e)
                        session.add(order)
                    
                    # Release Printer
                    if job.assigned_printer_serial:
                        printer = await session.get(Printer, job.assigned_printer_serial)
                        if printer:
                            printer.current_status = PrinterStatusEnum.IDLE
                            session.add(printer)
                            
                            logger.info(f"JOB {job_id}: Printer {printer.serial} released to IDLE due to failure.")
                
                await session.commit()
        except Exception as db_e:
            logger.error(f"JOB {job_id}: CRITICAL - Failed to update DB after job failure: {db_e}")
        

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
        # logger.debug("Sync Loop Tick...")
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
                                old_status = printer.current_status
                                new_status = printer.current_status # default

                                # Check for active job to protect UPLOADING state
                                active_job_q = await session.execute(
                                    select(Job).where(
                                        Job.assigned_printer_serial == printer.serial,
                                        col(Job.status).in_([JobStatusEnum.PRINTING, JobStatusEnum.UPLOADING])
                                    )
                                )
                                active_job_for_update = active_job_q.scalars().first()

                                if raw_status in ["IDLE", "FINISH", "FAILED"]:
                                    # Grace period: If job is UPLOADING, ignore IDLE
                                    if active_job_for_update and active_job_for_update.status == JobStatusEnum.UPLOADING:
                                        new_status = PrinterStatusEnum.PRINTING
                                    else:
                                        new_status = PrinterStatusEnum.IDLE
                                elif raw_status in ["RUNNING", "PAUSE", "PREPARE"]:
                                    new_status = PrinterStatusEnum.PRINTING
                                
                                # Check for Completion Transition (PRINTING -> IDLE)
                                if old_status == PrinterStatusEnum.PRINTING and new_status == PrinterStatusEnum.IDLE:
                                    logger.info(f"Printer {printer.serial} stopped printing (Status: {raw_status}). Checking for active job...")
                                    active_job_result = await session.execute(
                                        select(Job).where(
                                            Job.assigned_printer_serial == printer.serial,
                                            Job.status == JobStatusEnum.PRINTING
                                        )
                                    )
                                    active_job = active_job_result.scalars().first()
                                    
                                    if active_job:
                                        if raw_status == "FAILED":
                                             logger.error(f"Job {active_job.id} FAILED on printer. Updating status.")
                                             active_job.status = JobStatusEnum.FAILED
                                             active_job.error_message = "Printer reported FAILED state"
                                             session.add(active_job)
                                             
                                             order = await session.get(Order, active_job.order_id)
                                             if order:
                                                 order.status = OrderStatusEnum.FAILED
                                                 order.error_message = "Printer reported FAILED state"
                                                 session.add(order)
                                        else:
                                            logger.info(f"Job {active_job.id} COMPLETED. Updating status.")
                                            active_job.status = JobStatusEnum.FINISHED
                                            session.add(active_job)
                                            
                                            # Update Order to DONE
                                            order = await session.get(Order, active_job.order_id)
                                            if order:
                                                order.status = OrderStatusEnum.DONE
                                                session.add(order)
                                
                                if new_status != old_status:
                                    printer.current_status = new_status
                                    data_changed = True

                            if "nozzle_temper" in data:
                                printer.current_temp_nozzle = float(data["nozzle_temper"])
                                data_changed = True
                            
                            if "bed_temper" in data:
                                printer.current_temp_bed = float(data["bed_temper"])
                                data_changed = True
                            
                            if "ams_data" in data:
                                printer.ams_data = data["ams_data"]
                                data_changed = True
                            
                            if "progress" in data:
                                printer.current_progress = int(data["progress"])
                                data_changed = True
                            
                            if "remaining_time" in data:
                                printer.remaining_time = int(data["remaining_time"])
                                data_changed = True
                            
                            if data_changed:
                                session.add(printer)
                    
                    await session.commit()
                
                # --- STEP 1.5: Create Jobs from OPEN Orders ---
                # Check for OPEN orders that need processing
                result = await session.execute(
                    select(Order)
                    .where(Order.status == OrderStatusEnum.OPEN)
                    .order_by(Order.purchase_date.asc())
                )
                open_orders = result.scalars().all()
                
                for order in open_orders:
                    # Check if Job already exists (redundancy check)
                    # Ideally we update Order status to avoid this, but let's be safe
                    existing_job = await session.execute(select(Job).where(Job.order_id == order.id))
                    if existing_job.scalars().first():
                         # Just update status if needed
                         if order.status == OrderStatusEnum.OPEN:
                             order.status = OrderStatusEnum.QUEUED
                             session.add(order)
                         continue
                         
                    # Find Product
                    product_result = await session.execute(select(Product).where(Product.sku == order.sku))
                    product = product_result.scalars().first()
                    
                    if product:
                        logger.info(f"Creating Job for Order {order.id} (SKU: {order.sku})")
                        new_job = Job(
                            order_id=order.id,
                            gcode_path=product.file_path_3mf,
                            status=JobStatusEnum.PENDING,
                            created_at=datetime.now()
                        )
                        session.add(new_job)
                        
                        # Mark Order as QUEUED (Waiting for printer)
                        order.status = OrderStatusEnum.QUEUED
                        session.add(order)
                    else:
                        logger.error(f"Cannot create Job for Order {order.id}: Product SKU {order.sku} not found. Marking as DONE (Invalid).")
                        order.status = OrderStatusEnum.DONE
                        session.add(order)

                
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
                        matched_slot_idx = None
                        
                        # If no product found, we can't check requirements. 
                        # DECISION: Fail safe? Or unsafe? Let's assume unsafe and require product.
                        if not product:
                             logger.warning(f"Order {order.id} SKU {order.sku} not found in Products table. Cannot verify materials.")
                             # Skip or fail? Skipping for now.
                             continue

                        for p in idle_printers:
                            slot = check_material_match(p, product)
                            if slot is not None:
                                compatible_printer = p
                                matched_slot_idx = slot
                                break
                        
                        if compatible_printer and matched_slot_idx is not None:
                            # Assign
                            logger.info(f"Assigning Job {job.id} (Order {job.order_id}) to Printer {compatible_printer.serial} (Slot {matched_slot_idx})")
                            
                            job.assigned_printer_serial = compatible_printer.serial
                            job.status = JobStatusEnum.UPLOADING # Prevent race condition during upload
                            
                            # Update Order Status to PRINTING
                            order.status = OrderStatusEnum.PRINTING
                            session.add(order)

                            compatible_printer.current_status = PrinterStatusEnum.PRINTING
                            
                            session.add(job)
                            session.add(compatible_printer)
                            
                            # Remove from available pool for this loop
                            idle_printers.remove(compatible_printer)
                            
                            # COMMAND PRINTER
                            client = PRINTER_CLIENTS.get(compatible_printer.serial)
                            if client:
                                logger.info(f"JOB {job.id}: Triggering background print task for {compatible_printer.serial}")
                                # Pass matched slot as list [slot]
                                asyncio.create_task(execute_print_job(client, job.id, job.gcode_path, ams_mapping=[matched_slot_idx]))
                            else:
                                logger.error(f"JOB {job.id}: Fatal - No active client found for {compatible_printer.serial}")
                        else:
                            logger.debug(f"No compatible printer found for Job {job.id} (Req: {product.required_filament_type} {product.required_filament_color})")

                    if pending_jobs:
                        await session.commit()

        except Exception as e:
            logger.error(f"Error in sync_loop: {e}", exc_info=True)
        
        await asyncio.sleep(5)

def check_material_match(printer: Printer, product: Product) -> int:
    """
    Checks if the printer has the required filament loaded in AMS.
    Returns: Slot Index (int) if found, else None.
    """
    req_type = product.required_filament_type
    req_color = product.required_filament_color

    if not req_type:
        # No requirements, use Slot 0 (External/Spool Holder) or first available?
        # Let's default to AMS Slot 0 if available, else 0 essentially.
        return 0

    if not printer.ams_data:
        # No AMS data means we can't verify.
        logger.warning(f"Material Check Failed for {printer.serial}: No AMS Data available.")
        return None

    ams_slots = printer.ams_data # SQLModel/Postgres handles JSON decoding

    for slot in ams_slots:
        # Check standard format
        if not isinstance(slot, dict):
            continue
            
        slot_type = slot.get('type', 'UNKNOWN')
        slot_color = slot.get('color', None)
        remaining = slot.get('remaining', 0)
        slot_idx_str = slot.get('slot', '0')
        try:
            slot_idx = int(slot_idx_str)
        except:
            slot_idx = 0

        # 1. Empty Spool Check
        if remaining == 0:
            logger.warning(f"Slot warning: Spool reported empty (0%) in slot {slot_idx}, treating as available.")
            # continue # DISABLED: Allow printing on 0% for generic spools

        # 2. Type Check (Strict, Case Insensitive)
        if req_type.lower() != slot_type.lower():
            continue
        
        # 3. Color Check 
        if req_color:
            if not slot_color:
                continue
            # Simple exact match (case insensitive)
            if req_color.lower() != slot_color.lower():
                continue

        # Match Found! Return the slot index.
        return slot_idx

    logger.warning(f"Material Check Failed for {printer.serial}: No compatible slot found for {req_type} {req_color}")
    return None

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
                
                # Register in Global Dict
                PRINTER_CLIENTS[p.serial] = client
    
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
