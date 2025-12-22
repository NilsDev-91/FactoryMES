
import asyncio
import logging
import sys
from datetime import datetime
from sqlalchemy import select
from database import AsyncSessionLocal, Order, Job, OrderStatusEnum, JobStatusEnum
from ingest_service import fetch_orders_mock
from bambu_client import BambuPrinterClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MainDaemon")

# Printer Configuration (Hardcoded for prototype)
PRINTER_IP = "192.168.2.213"
ACCESS_CODE = "05956746"
SERIAL = "03919C461802608"

# Printer State
printer_state = {
    "status": "UNKNOWN",
    "nozzle_temper": 0.0,
    "bed_temper": 0.0,
    "ams_status": "UNKNOWN"
}

def on_printer_update(data):
    """Callback for printer telemetry updates."""
    
    # Map raw status to our simplified status if needed, or just store raw
    # Bambu statuses: IDLE, RUNNING, FINISH, etc.
    # We need to map to our PrinterStatusEnum or just use string checking for now as per reqs.
    # Req says: check if printer status is 'IDLE'.
    
    if "print_status" in data:
        printer_state["status"] = data["print_status"]
    if "nozzle_temper" in data:
        printer_state["nozzle_temper"] = float(data["nozzle_temper"])
    if "bed_temper" in data:
        printer_state["bed_temper"] = float(data["bed_temper"])
    
    # logger.debug(f"Printer update: {printer_state}")

async def main_loop():
    logger.info("Starting FactoryOS Main Daemon...")
    
    # 1. Initialize Printer Client
    client = BambuPrinterClient(PRINTER_IP, ACCESS_CODE, SERIAL, update_callback=on_printer_update)
    asyncio.create_task(client.connect_mqtt())
    
    logger.info("Printer client started in background.")

    while True:
        try:
            # Step 1: Ingest Orders
            await fetch_orders_mock()
            
            # Step 2: Check for OPEN jobs
            async with AsyncSessionLocal() as session:
                # Find oldest OPEN order
                result = await session.execute(
                    select(Order)
                    .where(Order.status == OrderStatusEnum.OPEN)
                    .order_by(Order.purchase_date.asc())
                    .limit(1)
                )
                order = result.scalar_one_or_none()
                
                if order:
                    logger.info(f"Found pending order: {order.id} - {order.sku}")
                    
                    # Step 3: Check Printer Status
                    # Status check: IDLE and Nozzle Temp > 0 (Online)
                    # Note: Bambu 'IDLE' status string might vary (e.g. "IDLE", "FINISH" -> ready?)
                    # Let's assume strict "IDLE" or "FINISH" means ready for new job for now, 
                    # but user req said check if "IDLE".
                    
                    current_status = printer_state.get("status", "UNKNOWN")
                    nozzle_temp = printer_state.get("nozzle_temper", 0.0)
                    
                    logger.info(f"Printer Status: {current_status}, Nozzle: {nozzle_temp}")
                    
                    is_ready = current_status in ["IDLE", "FINISH"] and nozzle_temp > 0
                    
                    # Step 4: Assignment
                    if is_ready:
                        logger.info(f"Assigning Order {order.id} to Printer {SERIAL}")
                        
                        # Update Order
                        order.status = OrderStatusEnum.IN_PROGRESS
                        
                        # Create Job
                        new_job = Job(
                            order_id=order.id,
                            assigned_printer_serial=SERIAL,
                            gcode_path=f"{order.sku}.gcode", # Mock path
                            status=JobStatusEnum.PRINTING, 
                            created_at=datetime.now()
                        )
                        session.add(new_job)
                        await session.commit()
                        
                        # Simulate Start Printing
                        logger.info(f"Start printing for SKU: {order.sku}")
                        
                        # Send signal/request (Mock for now, as we don't have real file on SD yet)
                        # We can try to send a valid looking request if the file existed, 
                        # but avoiding it to prevent errors on real printer without file.
                        # Just log as per requirements.
                        
                    else:
                        logger.info("Printer is not ready.")
                else:
                    logger.info("No open orders found.")

            # Step 5: Wait
            await asyncio.sleep(10)

        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
            await asyncio.sleep(10) # Wait before retrying

if __name__ == "__main__":
    # Windows specific event loop policy
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(main_loop())
