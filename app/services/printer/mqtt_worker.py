
import asyncio
import json
import logging
import ssl
import time
from typing import Dict, Any, Optional
from aiomqtt import Client, MqttError
import paho.mqtt.client as mqtt_base
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
        self._clients: Dict[str, Client] = {}
        self._state_cache: Dict[str, dict] = {} # Serial -> Full State Dict
        self._last_sync_time: Dict[str, float] = {} # Serial -> Timestamp
        self._background_tasks = set() # Prevent GC of running tasks

    async def start_listening(self, ip: str, access_code: str, serial: str):
        """
        Starts a background listener for a specific printer.
        """
        if serial in self._clients:
            logger.warning(f"Already listening to {serial}")
            return

        task = asyncio.create_task(self._run_client(ip, access_code, serial))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _run_client(self, ip: str, access_code: str, serial: str):
        """
        Main loop for a single printer connection using aiomqtt.
        """
        
        # Setup SSL
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        # OUTER LOOP: Ensure task NEVER dies, even on unforeseen crashes
        while True: 
            try:
                logger.info(f"Connecting to {serial} at {ip}:8883 (SSL/MQTT 3.1.1)...")
                
                try:
                    async with Client(
                        hostname=ip,
                        port=8883,
                        username="bblp",
                        password=access_code,
                        tls_context=context,
                        protocol=mqtt_base.MQTTv311, # FORCE 3.1.1 (Critical for Bambu)
                        identifier=f"worker_{serial}",
                        keepalive=30,
                        timeout=30.0
                    ) as client:
                        
                        self._clients[serial] = client
                        logger.info(f"Connected to {serial}")
                        
                        # Subscribe
                        topic = f"device/{serial}/report"
                        await client.subscribe(topic, qos=0)
                        logger.debug(f"Subscribed to {topic}")

                        # Message Loop
                        async for message in client.messages:
                            try:
                                payload = message.payload
                                if isinstance(payload, bytes):
                                    payload = payload.decode()
                                    
                                data = json.loads(payload)
                                # Async handling to not block the message loop
                                asyncio.create_task(self._handle_message(serial, data))
                                
                            except Exception as e:
                                logger.error(f"Error processing message from {serial}: {e}")

                except MqttError as e:
                     logger.warning(f"MQTT Connection lost for {serial}: {e}. Reconnecting in 5s...")
                except Exception as e:
                     logger.error(f"Unexpected MQTT Error for {serial}: {e}. Reconnecting in 5s...")
                
                # Cleanup logic if loop exits
                if serial in self._clients:
                    del self._clients[serial]
                
                await asyncio.sleep(5)

            except Exception as critical_e:
                logger.critical(f"CRITICAL: Outer Loop Crash for {serial}: {critical_e}. Restarting entire loop in 5s...", exc_info=True)
                await asyncio.sleep(5)

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
             # 1. Check if printer supports Auto-Ejection
             async with async_session_maker() as session:
                 printer = await session.get(Printer, serial)
                 if printer and printer.can_auto_eject:
                     logger.info(f"FMS: Printer {serial} supports Auto-Ejection. Bypassing Manual Clearance Protocol.")
                     updated_cache["is_plate_cleared"] = True
                     
                     # 2. Mark Job as FINISHED immediately
                     if printer.current_job_id:
                         job = await session.get(Job, printer.current_job_id)
                         if job:
                             logger.info(f"FMS: Force-Finishing Job {job.id} for auto-eject printer {serial}.")
                             job.status = JobStatusEnum.FINISHED
                             session.add(job)
                         
                         printer.current_job_id = None # Clear active job
                         session.add(printer)
                         await session.commit()
                 else:
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

                            if not tray_data:
                                # EMPTY SLOT: Clear fields
                                target_slot.tray_color = None
                                target_slot.tray_type = None
                                target_slot.remaining_percent = None
                                # Do NOT delete the slot, just clear it.
                                session.add(target_slot)
                                
                            else:
                                # OCCUPIED SLOT: Update fields
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
        Auto-Advance Logic: Find compatible pending jobs and execute.
        Bypasses deadlocks by peeking for the first compatible job.
        """
        async with async_session_maker() as session:
            job_service = JobService()
            fms = FilamentManager()
            commander = PrinterCommander()
            executor = PrintJobExecutionService(session, fms, commander)
            
            # 1. Safety Latch Check (DB Truth)
            printer = await session.get(Printer, serial)
            if not printer:
                logger.error(f"Printer {serial} not found during queue processing.")
                return

            if not printer.is_plate_cleared:
                logger.warning(f"Printer {serial} IDLE, but Plate is Dirty. Waiting for operator release.")
                return 

            # 2. Smart Peeking: Find a job this printer can actually print
            job = await job_service.get_next_compatible_job_for_printer(session, printer, fms)
            
            if not job:
                # 3. Smart Backoff: Avoid spinning CPU if no compatible jobs exist
                logger.info(f"No compatible jobs found for {serial}. Cooling down (10s backoff)...")
                await asyncio.sleep(10)
                return

            logger.info(f"Found compatible Job {job.id} for {serial}. Attempting execution...")
            
            try:
                # 4. Execute (this checks FMS and dispatches)
                await executor.execute_print_job(job.id, serial)
                logger.info(f"Job {job.id} successfully started on {serial}.")
                
            except ValueError as e:
                # Domain error (e.g. material mismatch confirmed during dispatch)
                logger.warning(f"Failed to execute compatible Job {job.id} on {serial}: {e}")
                
            except Exception as e:
                logger.error(f"Unexpected error executing Job {job.id} on {serial}: {e}")
