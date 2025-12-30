
import asyncio
import json
import logging
import ssl
import time
from typing import Dict, Any, Optional
from gmqtt import Client as MQTTClient, constants
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.core import Printer, PrinterStatusEnum
from app.models.filament import AmsSlot
from app.services.print_job_executor import PrintJobExecutionService
from app.services.job_service import JobService
from app.services.filament_manager import FilamentManager
from app.services.printer.commander import PrinterCommander


logger = logging.getLogger("PrinterMqttWorker")

# Status Mapping
GCODE_STATE_MAP = {
    "IDLE": PrinterStatusEnum.IDLE,
    "RUNNING": PrinterStatusEnum.PRINTING,
    "FINISH": PrinterStatusEnum.AWAITING_CLEARANCE, # Manual Clearance Protocol
    "PAUSE": PrinterStatusEnum.IDLE, # Or handle as separate status
    "OFFLINE": PrinterStatusEnum.OFFLINE
}

class PrinterMqttWorker:
    def __init__(self):
        self._clients: Dict[str, MQTTClient] = {}
        self._state_cache: Dict[str, dict] = {} # Serial -> Full State Dict
        self._last_sync_time: Dict[str, float] = {} # Serial -> Timestamp

    async def start_listening(self, ip: str, access_code: str, serial: str):
        """
        Starts a background listener for a specific printer.
        """
        if serial in self._clients:
            logger.warning(f"Already listening to {serial}")
            return

        asyncio.create_task(self._run_client(ip, access_code, serial))

    async def _run_client(self, ip: str, access_code: str, serial: str):
        """
        Main loop for a single printer connection.
        """
        client = MQTTClient(client_id=f"worker_{serial}")
        client.set_auth_credentials("bblp", access_code)
        
        # Setup SSL
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        # Callbacks
        client.on_message = self._create_on_message(serial)
        client.on_connect = self._create_on_connect(serial)
        client.on_disconnect = self._create_on_disconnect(serial)

        while True:
            try:
                logger.info(f"Connecting to {serial} at {ip}:8883 (SSL)...")
                
                # Increased timeout to 30.0s for better stability on busy networks
                try:
                    await asyncio.wait_for(
                        client.connect(ip, 8883, ssl=context, version=constants.MQTTv311, keepalive=30),
                        timeout=30.0
                    )
                except asyncio.TimeoutError:
                    logger.error(f"Printer Connection TIMEOUT: {serial} at {ip} did not respond within 30s.")
                    raise
                except ConnectionRefusedError:
                    logger.error(f"Printer Connection REFUSED: {serial} at {ip}. Is the printer online and MQTT enabled?")
                    raise
                except Exception as e:
                    logger.error(f"Printer Connection FAILED: {serial} at {ip} with error: {type(e).__name__}: {e}")
                    raise
                
                # Keep alive until disconnect
                STOP = asyncio.Event()
                self._clients[serial] = client
                
                await STOP.wait()

            except (asyncio.TimeoutError, Exception):
                # Generic reconnect delay
                logger.info(f"Retrying connection to {serial} in 10s...")
                await asyncio.sleep(10)
            finally:
                try:
                    await client.disconnect()
                except:
                    pass

    def _create_on_connect(self, serial: str):
        def on_connect(client, flags, rc, properties):
            logger.info(f"Connected to {serial}")
            client.subscribe(f"device/{serial}/report", qos=0)
        return on_connect

    def _create_on_disconnect(self, serial: str):
        def on_disconnect(client, packet, exc=None):
            logger.warning(f"Disconnected from {serial}")
        return on_disconnect

    def _create_on_message(self, serial: str):
        def on_message(client, topic, payload, qos, properties):
            try:
                data = json.loads(payload)
                asyncio.create_task(self._handle_message(serial, data))
            except Exception as e:
                logger.error(f"Error handling message from {serial}: {e}")
        return on_message

    async def _handle_message(self, serial: str, message: dict):
        """
        Process the message:
        1. Deep merge into cache.
        2. Check for critical status change.
        3. Sync to DB if throttled allowed or critical.
        """
        # Bambu messages are usually wrapped in "print" key
        # e.g. {"print": {"gcode_state": ...}}
        print_data = message.get("print", {})
        if not print_data:
            return

        # 1. Update Cache
        current_cache = self._state_cache.get(serial, {})
        updated_cache = self._deep_merge(current_cache, print_data)
        self._state_cache[serial] = updated_cache
        
        # 2. Check Throttling
        should_sync = False
        now = time.time()
        last_sync = self._last_sync_time.get(serial, 0)
        
        # Check Status Change
        old_status = current_cache.get("gcode_state")
        new_status = print_data.get("gcode_state")
        
        if new_status and old_status != new_status:
            should_sync = True
            logger.info(f"Status change detected for {serial}: {old_status} -> {new_status}")
            
        if new_status == "FINISH":
             logger.warning(f"Print finished on {serial}. Safety Latch ENGAGED (Plate Dirty).")
             updated_cache["is_plate_cleared"] = False
             should_sync = True
         
        # Check Time
        if (now - last_sync) > 5.0:
            should_sync = True
            
        if should_sync:
            await self._sync_to_db(serial, updated_cache)
            self._last_sync_time[serial] = now

        # 3. Auto-Advance Queue Logic
        # Trigger: Transition to IDLE
        current_data = self._state_cache.get(serial, {})
        new_gcode_state = print_data.get("gcode_state")
        
        # We need previous state to detect transition, but we already merged.
        # However, we can check if current status in DB is NOT IDLE (via sync) or rely on `old_status` variable if available in scope.
        # `old_status` was captured before merge? No, `current_cache` was fetched before merge.
        # So `old_status` is valid.
        
        if new_gcode_state == "IDLE" and old_status != "IDLE":
             # Check if Plate is Cleared (using cache which is latest truth roughly, but DB is safer source of truth for the flag)
             # However, we just updated cache.
             is_plate_cleared = updated_cache.get("is_plate_cleared", True) # Default true if unknown? No, better check DB or assume True if missing.
             # Actually, we should check the DB in the async task to be race-proof.
             
             logger.info(f"Printer {serial} transitioned to IDLE. Attempting to advance queue...")
             asyncio.create_task(self._process_queue_for_printer(serial))


    def _deep_merge(self, current: dict, update: dict) -> dict:
        """
        Recursive Deep Merge of two dictionaries.
        """
        result = current.copy()
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    async def _sync_to_db(self, serial: str, state: dict):
        """
        Syncs critical state to Database.
        """
        try:
            async with async_session_maker() as session:
                # 1. Get Printer
                printer = await session.get(Printer, serial)
                if not printer:
                    logger.warning(f"Printer {serial} not found in DB, skipping sync.")
                    return

                # 2. Update Printer Fields
                if "gcode_state" in state:
                    status_str = state["gcode_state"]
                    # Default to IDLE if unknown map
                    printer.current_status = GCODE_STATE_MAP.get(status_str, PrinterStatusEnum.IDLE)
                
                if "nozzle_temper" in state:
                    printer.current_temp_nozzle = float(state["nozzle_temper"])
                    
                if "bed_temper" in state:
                    printer.current_temp_bed = float(state["bed_temper"])
                    
                if "mc_percent" in state:
                    printer.current_progress = int(state["mc_percent"])
                    
                if "mc_remaining_time" in state:
                    printer.remaining_time = int(state["mc_remaining_time"])
                    
                if "is_plate_cleared" in state:
                    printer.is_plate_cleared = state["is_plate_cleared"]
                    
                # 3. Update AMS Slots
                # API structure: state['ams']['ams'][ams_index]['tray'][tray_index]
                if "ams" in state and "ams" in state["ams"]:
                    ams_list = state["ams"]["ams"]
                    
                    # We need to fetch existing slots to update them efficiently? 
                    # OR we iterate what we have in cache.
                    # Best effort: Update slots that exist in DB matching current ams/tray index.
                    
                    # Pre-load slots to map efficiently
                    # But we can just iterate and update if attached to session
                    await session.refresh(printer, ["ams_slots"])
                    
                    for ams_idx, ams_unit in enumerate(ams_list):
                        tray_list = ams_unit.get("tray", [])
                        for tray_idx, tray_data in enumerate(tray_list):
                            # Find matching slot in printer.ams_slots
                            # Optimization: Could map by (ams, slot) first, but list is small (4-16)
                            target_slot = None
                            for slot in printer.ams_slots:
                                if slot.ams_index == ams_idx and slot.slot_index == tray_idx:
                                    target_slot = slot
                                    break
                            
                            if not target_slot:
                                target_slot = AmsSlot(
                                    printer_id=printer.serial,
                                    ams_index=ams_idx,
                                    slot_index=tray_idx,
                                    tray_color="",
                                    tray_type=""
                                )
                                session.add(target_slot)
                                printer.ams_slots.append(target_slot)

                            if tray_data:
                                # Update Slot
                                # Colors from Bambu are often like "FF00FF00" (RGBA?) or just Hex. 
                                # We treat as Hex string.
                                if "tray_color" in tray_data:
                                    target_slot.tray_color = tray_data["tray_color"]
                                
                                if "tray_type" in tray_data:
                                    target_slot.tray_type = tray_data["tray_type"]
                                    
                                if "remain" in tray_data:
                                    target_slot.remaining_percent = int(tray_data["remain"])
                                    
                                session.add(target_slot)

                session.add(printer)
                await session.commit()
                
        except Exception as e:
            logger.error(f"DB Sync failed for {serial}: {e}")


    async def _process_queue_for_printer(self, serial: str):
        """
        Auto-Advance Logic: Find pending jobs and execute them.
        """
        async with async_session_maker() as session:
            job_service = JobService()
            fms = FilamentManager()
            commander = PrinterCommander()
            executor = PrintJobExecutionService(session, fms, commander)
            
            # Safety Latch Check (DB Truth)
            printer = await session.get(Printer, serial)
            if not printer:
                logger.error(f"Printer {serial} not found during queue processing.")
                return

            if not printer.is_plate_cleared:
                logger.warning(f"Printer {serial} IDLE, but Plate is Dirty. Waiting for operator release.")
                return 

            # Retry Loop (limit 5 attempts to avoid infinite churning on bad queue)
            for _ in range(5):
                job = await job_service.get_next_pending_job(session)
                if not job:
                    logger.info(f"No pending jobs found for {serial}.")
                    break
                
                logger.info(f"Found Job {job.id} for {serial}. Attempting execution...")
                
                try:
                    # Execute (this checks FMS and dispatches)
                    await executor.execute_print_job(job.id, serial)
                    logger.info(f"Job {job.id} successfully started on {serial}.")
                    break # Success, stop loop
                    
                except ValueError as e:
                    # Mismatch or other domain error.
                    # Executor already updates Job Status to FAILED/MATERIAL_MISMATCH.
                    # We just log and continue to next job.
                    logger.warning(f"Skipping Job {job.id} due to error: {e}")
                    continue
                    
                except Exception as e:
                    logger.error(f"Unexpected error executing Job {job.id}: {e}")
                    # Job might rely on Executor's internal error handling to set FAILED.
                    # If Executor raised creates unhandled state, ensure we don't loop forever on same job.
                    # If job valid but failing systematically, we should probably SKIP it or it stays PENDING?
                    # Executor `execute_print_job` updates status to FAILED on generic exception too.
                    # So it shouldn't be PENDING anymore.
                    continue
