
import asyncio
import logging
import sys
from datetime import datetime
from typing import Dict, Optional, Any
from sqlalchemy import select
# Note: database.py usually exports 'async_session_maker' or similar. 
# We alias it to AsyncSessionLocal for clarity if that was the convention, 
# or just use it directly. Assuming async_session_maker is available.
from database import async_session_maker
from models import Printer, Order, Job, OrderStatusEnum, JobStatusEnum, PrinterStatusEnum
from ingest_service import fetch_orders_mock
from bambu_client import BambuPrinterClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FleetManager")

class PrinterConnection:
    """
    Wraps a BambuPrinterClient to add state tracking and traffic control logic.
    """
    def __init__(self, serial: str, client: BambuPrinterClient):
        self.serial = serial
        self.client = client
        self.last_known_state = {
            "status": "UNKNOWN",
            "nozzle_temper": 0.0,
            "bed_temper": 0.0
        }
        self.last_db_write_time = 0.0 # epoch timestamp
        
    def should_write_to_db(self, new_data: Dict[str, Any]) -> bool:
        """
        Determines if we should write to DB based on traffic control rules.
        Rules:
        1. Status changed (e.g. IDLE -> PRINTING)
        2. Temp changed > 2 degrees
        3. Heartbeat > 30s elapsed since last write
        """
        now = datetime.now().timestamp()
        
        # Rule 3: Heartbeat
        if (now - self.last_db_write_time) > 30:
            return True
            
        # Parse new data
        new_status = new_data.get("print_status", self.last_known_state["status"])
        new_nozzle = float(new_data.get("nozzle_temper", self.last_known_state["nozzle_temper"]))
        new_bed = float(new_data.get("bed_temper", self.last_known_state["bed_temper"]))
        
        # Rule 1: Status Change
        if new_status != self.last_known_state["status"]:
            return True
            
        # Rule 2: Significant Temp Change (> 2.0C)
        if abs(new_nozzle - self.last_known_state["nozzle_temper"]) > 2.0:
            return True
        if abs(new_bed - self.last_known_state["bed_temper"]) > 2.0:
            return True
            
        return False

    def update_state(self, new_data: Dict[str, Any]):
        """Updates the local state cache."""
        if "print_status" in new_data:
            self.last_known_state["status"] = new_data["print_status"]
        if "nozzle_temper" in new_data:
            self.last_known_state["nozzle_temper"] = float(new_data["nozzle_temper"])
        if "bed_temper" in new_data:
             self.last_known_state["bed_temper"] = float(new_data["bed_temper"])

class FleetManager:
    def __init__(self):
        self.active_printers: Dict[str, PrinterConnection] = {}
        
    async def refresh_fleet(self):
        """
        Loads all printers from the DB. 
        Instantiates new clients for any we don't haven't connected to yet.
        """
        logger.info("Refreshing fleet configuration from DB...")
        async with async_session_maker() as session:
            result = await session.execute(select(Printer))
            db_printers = result.scalars().all()
            
            for p in db_printers:
                if p.serial not in self.active_printers:
                    if not p.ip_address or not p.access_code:
                        logger.warning(f"Skipping printer {p.serial} (Missing IP/Access Code)")
                        continue
                        
                    logger.info(f"Initializing new printer: {p.name} ({p.serial})")
                    
                    # Create Client
                    client = BambuPrinterClient(
                        ip=p.ip_address,
                        access_code=p.access_code,
                        serial=p.serial,
                        update_callback=lambda d, s=p.serial: self.handle_printer_update(s, d)
                    )
                    
                    # Create Wrapper
                    connection = PrinterConnection(p.serial, client)
                    self.active_printers[p.serial] = connection
                    
                    # Start Connection Background Task
                    asyncio.create_task(self.safe_connect(connection))
            
            logger.info(f"Fleet refresh complete. Active units: {len(self.active_printers)}")

    async def safe_connect(self, connection: PrinterConnection):
        """Wraps connection logic in error handler to prevent crashing main loop."""
        try:
            await connection.client.connect_mqtt()
        except Exception as e:
            logger.error(f"Printer {connection.serial} connection failed: {e}")
            # We could implement retry logic here or rely on the client's internal retry

    def handle_printer_update(self, serial: str, data: Dict[str, Any]):
        """
        Callback triggered by BambuPrinterClient when MQTT data arrives.
        This runs in the loop but is synchronous in origin, so we schedule async DB writes.
        """
        if serial not in self.active_printers:
            return

        conn = self.active_printers[serial]
        
        # 1. Check Traffic Control logic
        if conn.should_write_to_db(data):
            # 2. Update local state
            conn.update_state(data)
            conn.last_db_write_time = datetime.now().timestamp()
            
            # 3. Schedule Async DB Persist
            asyncio.create_task(self.persist_printer_state(serial, conn.last_known_state))
        else:
            # Update local state anyway for potential logic usage, but skip DB
            # (Optional: might want to throttle local updates too if very high freq, 
            # but usually cheap compared to DB)
            conn.update_state(data)

    async def persist_printer_state(self, serial: str, state: Dict[str, Any]):
        """Writes current state to DB."""
        # Map string status to Enum
        # Bambu: IDLE, RUNNING, PAUSE, FINISH, OFFLINE
        raw_status = state.get("status", "UNKNOWN")
        mapped_status = PrinterStatusEnum.PRINTING # Default fail-safe
        
        if raw_status == "IDLE":
            mapped_status = PrinterStatusEnum.IDLE
        elif raw_status == "FINISH":
            mapped_status = PrinterStatusEnum.IDLE # Treated as ready
        elif raw_status == "OFFLINE":
             mapped_status = PrinterStatusEnum.OFFLINE
        
        # "RUNNING", "PREPARE" -> PRINTING
        
        try:
            async with async_session_maker() as session:
                stmt = select(Printer).where(Printer.serial == serial)
                result = await session.execute(stmt)
                printer = result.scalar_one_or_none()
                
                if printer:
                    printer.current_status = mapped_status
                    printer.current_temp_nozzle = state.get("nozzle_temper", 0.0)
                    printer.current_temp_bed = state.get("bed_temper", 0.0)
                    session.add(printer)
                    await session.commit()
                    # logger.info(f"Persisted state for {serial}: {mapped_status}")
        except Exception as e:
            logger.error(f"DB Write Error for {serial}: {e}")

async def main_loop():
    logger.info("Starting FactoryOS Fleet Manager...")
    
    # Initialize Fleet Manager
    fleet = FleetManager()
    
    # Initial Fleet Load
    await fleet.refresh_fleet()

    while True:
        try:
            # --- Business Logic Loop ---
            
            # 1. Ingest Orders (Mock)
            await fetch_orders_mock()
            
            # 2. Assign Jobs
            async with async_session_maker() as session:
                # Find oldest OPEN order
                result = await session.execute(
                    select(Order)
                    .where(Order.status == OrderStatusEnum.OPEN)
                    .order_by(Order.purchase_date.asc())
                    .limit(1)
                )
                order = result.scalar_one_or_none()
                
                if order:
                    logger.info(f"Processing Pending Order: {order.sku}")
                    
                    # Find a Ready Printer from our Active Fleet
                    candidate_printer = None
                    
                    # Check our local 'active_printers' cache first for speed?
                    # Or query DB? 
                    # querying DB is safer for "Source of Truth" lock, 
                    # but we have local state. Let's query DB to check 'IDLE' 
                    # and ensure we pick one that is actually online (in fleet).
                    
                    # Simple strategy: Iterate local fleet, find IDLE
                    for serial, conn in fleet.active_printers.items():
                        # Check local state cache
                        if conn.last_known_state["status"] in ["IDLE", "FINISH"]:
                             # Double check connection?
                             if conn.client.connected:
                                 candidate_printer = serial
                                 break
                    
                    if candidate_printer:
                        logger.info(f"Assigning Order {order.id} to Printer {candidate_printer}")
                        
                        # Update Order
                        order.status = OrderStatusEnum.IN_PROGRESS
                        
                        # Create Job
                        new_job = Job(
                            order_id=order.id,
                            assigned_printer_serial=candidate_printer,
                            gcode_path=f"{order.sku}.gcode",
                            status=JobStatusEnum.PRINTING, 
                            created_at=datetime.now()
                        )
                        session.add(new_job)
                        await session.commit()
                        
                        logger.info(f"Job Created. Dispatching start command...")
                        
                        # Dispatch Command via Fleet Manager
                        if candidate_printer in fleet.active_printers:
                             client = fleet.active_printers[candidate_printer].client
                             # Mock Gcode path
                             await client.send_gcode_path(f"{order.sku}.gcode")
                    else:
                        logger.info("No available printers.")
            
            # 3. Wait
            await asyncio.sleep(5)
            
            # 4. Occasional Fleet Refresh (e.g. every min)? 
            # For now, just once at start is fine, or simple counter.

        except Exception as e:
            logger.error(f"Global Loop Error: {e}", exc_info=True)
            await asyncio.sleep(5)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(main_loop())
