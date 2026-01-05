
import asyncio
import json
import logging
import ssl
import time
from typing import Dict, Any, Optional, Set
from datetime import datetime, timezone
from aiomqtt import Client, MqttError
import paho.mqtt.client as mqtt_base
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import async_session_maker
from app.models.core import Printer, PrinterStatusEnum, ClearingStrategyEnum, JobStatusEnum
from app.models.filament import AmsSlot
from app.services.print_job_executor import PrintJobExecutionService
from app.services.printer.commander import PrinterCommander
from app.services.production.bed_clearing_service import BedClearingService
from app.services.logic.hms_parser import HMSParser, hms_parser, ErrorSeverity, ErrorModule
from app.services.job_dispatcher import job_dispatcher
from app.core.redis import get_redis_client
from app.schemas.printer_cache import PrinterStateCache, AMSSlotCache


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
        # Phase 7: HMS Error Tracking (Idempotency)
        self._last_error_codes: Dict[str, Set[str]] = {} # Serial -> Set of active error codes

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
        
        # Phase 7: HMS Watchdog - Parse Error Codes
        hms_codes = print_data.get("hms", [])
        print_error = print_data.get("print_error", 0)
        
        if hms_codes:
            await self._handle_hms_errors(serial, hms_codes, updated_cache)
        
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
                # IF we were CLEARING_BED, this FINISH means the clearing is done
                # Note: old_status is from current_cache (pre-merge)
                async with async_session_maker() as session:
                    printer = await session.get(Printer, serial)
                    if not printer: return

                    # Create Executor
                    from app.services.filament_manager import FilamentManager
                    fms = FilamentManager() # Lightweight
                    commander = PrinterCommander() # Lightweight
                    executor = PrintJobExecutionService(session, fms, commander)

                    if printer.current_status == PrinterStatusEnum.CLEARING_BED:
                        logger.info(f"♻️ Infinite Loop Cycle Complete. Printer {serial} reset to IDLE. Plate is now CLEARED.")
                        printer.current_status = PrinterStatusEnum.IDLE
                        printer.is_plate_cleared = True
                        session.add(printer)
                        await session.commit()
                        updated_cache["is_plate_cleared"] = True
                        
                        # Loop Closure: Trigger Dispatcher immediately to reduce idle time
                        logger.info(f"Loop Closure: Triggering immediate dispatch for {serial}")
                        asyncio.create_task(job_dispatcher.dispatch_next_job(session))
                        return # Exit, don't fallback to handle_print_finished
                    
                    # Standard Job Workflow (Delegate to Executor)
                    await executor.handle_print_finished(serial)
                    # Refresh printer state after executor might have changed it (e.g. COOLDOWN)
                    await session.refresh(printer)
                    updated_cache["current_status"] = printer.current_status
                    updated_cache["is_plate_cleared"] = printer.is_plate_cleared
                    
                    # FORCE CACHE UPDATE so _sync_to_db doesn't overwrite
                    updated_cache["is_plate_cleared"] = printer.is_plate_cleared
                            # We can't easily map internal Enum back to "gcode_state" string perfecty, 
                            # but _sync_to_db respects COOLDOWN/CLEARING_BED/AWAITING_CLEARANCE.
                            # Just need to make sure we don't accidentally set it to IDLE if we are waiting.
                            # Actually, if we are COOLDOWN, "gcode_state" is likely still "FINISH".
                            # _sync_to_db maps FINISH -> AWAITING_CLEARANCE.
                            # But if printer.status is COOLDOWN, _sync_to_db ignores the map.
                            # So we are SAFE.
         
        # Check Time
        if (now - last_sync) > 5.0:
            should_sync = True
            
        if should_sync:
            await self._sync_to_db(serial, updated_cache)
            await self._sync_to_redis(serial, updated_cache)  # RESTORE TELEMETRY
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

    async def _handle_hms_errors(self, serial: str, hms_codes: list, cache: dict):
        """
        Phase 7: HMS Watchdog - Handle hardware errors from MQTT.
        
        Parses HMS codes and reacts:
        - CRITICAL during CLEARING_BED -> ERROR (The Sweep failed)
        - CRITICAL during PRINTING -> PAUSED (User intervention)
        - Logs error to database with human-readable description
        """
        # Parse codes
        events = hms_parser.parse(hms_codes)
        if not events:
            return
        
        # Get most severe
        most_severe = hms_parser.get_most_severe(events)
        if not most_severe:
            return
        
        # Idempotency: Check if this is a new error
        if serial not in self._last_error_codes:
            self._last_error_codes[serial] = set()
        
        current_codes = set(e.code for e in events)
        new_codes = current_codes - self._last_error_codes[serial]
        
        if not new_codes:
            # Same errors as before, don't spam
            return
        
        # Update tracked codes
        self._last_error_codes[serial] = current_codes
        
        # Log all new errors
        for code in new_codes:
            event = next((e for e in events if e.code == code), None)
            if event:
                logger.warning(f"HMS [{serial}]: {event.severity.value} - {event.description} (Module: {event.module.value})")
        
        # React to CRITICAL errors
        if hms_parser.has_critical(events):
            await self._handle_critical_error(serial, most_severe)

    async def _handle_critical_error(self, serial: str, event):
        """
        Handle a CRITICAL HMS error - transition to ERROR state.
        """
        logger.error(f"CRITICAL HMS ERROR on {serial}: {event.description}")
        
        async with async_session_maker() as session:
            printer = await session.get(Printer, serial)
            if not printer:
                return
            
            # Determine new status based on current state
            if printer.current_status == PrinterStatusEnum.CLEARING_BED:
                # The Gantry Sweep FAILED - this is a critical failure
                logger.error(f"GANTRY SWEEP FAILURE on {serial}: {event.description}")
                new_status = PrinterStatusEnum.ERROR
            elif printer.current_status == PrinterStatusEnum.PRINTING:
                # Filament or motion error during print - pause for intervention
                if event.module == ErrorModule.AMS:
                    logger.warning(f"Filament error during print on {serial}: {event.description}")
                    new_status = PrinterStatusEnum.PAUSED
                else:
                    new_status = PrinterStatusEnum.ERROR
            else:
                # Any other critical error
                new_status = PrinterStatusEnum.ERROR
            
            # Update printer state
            printer.current_status = new_status
            printer.last_error_code = event.code
            printer.last_error_time = datetime.now(timezone.utc)
            printer.last_error_description = event.description
            
            session.add(printer)
            await session.commit()
            
            logger.info(f"Printer {serial} transitioned to {new_status.value} due to HMS error")


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
                    new_mapped_status = GCODE_STATE_MAP.get(status_str, PrinterStatusEnum.IDLE)
                    
                    # THE STATE MACHINE SAFETY LATCH
                    # If we are in COOLDOWN, CLEARING_BED, ERROR, or PAUSED, do not allow MQTT telemetry 
                    # to reset us until the condition is explicitly cleared.
                    protected_states = [
                        PrinterStatusEnum.COOLDOWN, 
                        PrinterStatusEnum.CLEARING_BED,
                        PrinterStatusEnum.ERROR,
                        PrinterStatusEnum.PAUSED
                    ]
                    if printer.current_status in protected_states:
                        # Only transition out via internal logic or if printer goes OFFLINE
                        if new_mapped_status == PrinterStatusEnum.OFFLINE:
                            printer.current_status = PrinterStatusEnum.OFFLINE
                        else:
                            # Remain in current protected state
                            logger.debug(f"Printer {serial} is in {printer.current_status}. Ignoring telemetry status {status_str}.")
                    else:
                        printer.current_status = new_mapped_status
                
                # --- THERMAL WATCHDOG (COOLDOWN -> CLEARING_BED) ---
                if printer.current_status == PrinterStatusEnum.COOLDOWN:
                    # Physical Principle: Monitor BED temperature for part detachment release
                    current_bed = float(state.get("bed_temper", printer.current_temp_bed))
                    if current_bed <= printer.thermal_release_temp:
                         logger.info(f"Thermal Release reached ({current_bed}°C). Triggering Bed Clearing for {serial}.")
                         # Trigger Ejection in background to not block sync
                         asyncio.create_task(self._trigger_ejection(serial))
                
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
                            
                            # Global Slot Index (0-15) for easy dispatching
                            slot_id = (ams_idx * 4) + tray_idx

                            if not target_slot:
                                target_slot = AmsSlot(
                                    printer_id=printer.serial,
                                    ams_index=ams_idx,
                                    slot_index=tray_idx,
                                    slot_id=slot_id,
                                    color_hex="",
                                    material=""
                                )
                                session.add(target_slot)
                                printer.ams_slots.append(target_slot)

                            if not tray_data:
                                # EMPTY SLOT: Clear fields
                                target_slot.color_hex = None
                                target_slot.material = None
                                target_slot.remaining_percent = None
                                # Do NOT delete the slot, just clear it.
                                session.add(target_slot)
                                
                            else:
                                # OCCUPIED SLOT: Update fields
                                if "tray_color" in tray_data:
                                    target_slot.color_hex = tray_data["tray_color"]
                                
                                if "tray_type" in tray_data:
                                    target_slot.material = tray_data["tray_type"]
                                    
                                if "remain" in tray_data:
                                    target_slot.remaining_percent = int(tray_data["remain"])
                                    
                                session.add(target_slot)

                session.add(printer)
                await session.commit()
                
        except Exception as e:
            logger.error(f"DB Sync failed for {serial}: {e}")

    async def _sync_to_redis(self, serial: str, state: dict):
        """
        Syncs full telemetry to Redis for UI consumption.
        Matches the Sentinel schema for frontend compatibility.
        """
        try:
            # 1. Map status
            # Use cached gcode_state if present, otherwise default to OFFLINE
            status_str = state.get("gcode_state")
            if not status_str:
                # Fallback: If we have temps but no state, we are at least IDLE
                if state.get("nozzle_temper", 0) > 0:
                    status = PrinterStatusEnum.IDLE
                else:
                    status = PrinterStatusEnum.OFFLINE
            else:
                status = GCODE_STATE_MAP.get(status_str, PrinterStatusEnum.IDLE)
            
            # 2. Extract AMS
            ams_cache_list = []
            ams_data = state.get("ams", {}).get("ams", [])
            for ams_unit in ams_data:
                ams_id = ams_unit.get("id", "0")
                trays = ams_unit.get("tray", [])
                for tray in trays:
                    tray_id = tray.get("id", "0")
                    global_slot_id = (int(ams_id) * 4) + int(tray_id)
                    ams_cache_list.append(AMSSlotCache(
                        slot_id=global_slot_id,
                        color=tray.get("tray_color"),
                        material=tray.get("tray_type")
                    ))

            # 3. Create Cache Model
            cache = PrinterStateCache(
                serial=serial,
                status=status,
                temps={
                    "nozzle": float(state.get("nozzle_temper", 0.0)),
                    "bed": float(state.get("bed_temper", 0.0))
                },
                progress=int(state.get("mc_percent", 0)),
                remaining_time_min=int(state.get("mc_remaining_time", 0)),
                active_file=state.get("subtask_name"),
                ams=ams_cache_list,
                updated_at=time.time()
            )

            # 4. Redis Write (60s TTL)
            redis = get_redis_client()
            key = f"printer:{serial}:status"
            await redis.set(key, cache.model_dump_json(), ex=60)
            logger.debug(f"Telemetry synced to Redis for {serial}")

        except Exception as e:
            logger.error(f"Redis Sync failed for {serial}: {e}")


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
            stmt = select(Printer).where(Printer.serial == serial).options(selectinload(Printer.ams_slots))
            result = await session.execute(stmt)
            printer = result.scalars().first()
            
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

    async def _trigger_ejection(self, serial: str):
        """
        Orchestrates the physical clearing of the part via PrintJobExecutor.
        """
        try:
            async with async_session_maker() as session:
                fms = FilamentManager()
                commander = PrinterCommander()
                # BedClearingService is instantiated internally by Executor or we pass it
                # Executor __init__ defaults bed_clearing_service=None -> creates new one.
                executor = PrintJobExecutionService(session, fms, commander)
                
                await executor.trigger_clearing(serial)

        except Exception as e:
            logger.error(f"Ejection trigger failed for {serial}: {e}", exc_info=True)
            async with async_session_maker() as session:
                printer = await session.get(Printer, serial)
                if printer:
                    printer.current_status = PrinterStatusEnum.AWAITING_CLEARANCE # Fallback to manual
                    session.add(printer)
                    await session.commit()
