
import asyncio
import json
import logging
import ssl
import time
from typing import Dict, Any, Optional
from gmqtt import Client as MQTTClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.core import Printer, PrinterStatusEnum
from app.models.filament import AmsSlot

logger = logging.getLogger("PrinterMqttWorker")

# Status Mapping
GCODE_STATE_MAP = {
    "IDLE": PrinterStatusEnum.IDLE,
    "RUNNING": PrinterStatusEnum.PRINTING,
    "FINISH": PrinterStatusEnum.IDLE, # Finish is technically IDLE but we might want to flag it?
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
                logger.info(f"Connecting to {serial} at {ip}...")
                await client.connect(ip, 8883, ssl=context)
                
                # Keep alive until disconnect
                # gmqtt client needs to be awaited or run in loop?
                # Usually we wait on a future or signal.
                # But here we stick to the pattern of 'connect' and just wait. 
                # gmqtt doesn't block on connect, so we need a keep-alive loop.
                # But actually gmqtt usage usually involves client.connect() then main loop?
                STOP = asyncio.Event()
                await STOP.wait() # Wait forever potentially

            except Exception as e:
                logger.error(f"Connection lost to {serial}: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)
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
        
        # Check Time
        if (now - last_sync) > 5.0:
            should_sync = True
            
        if should_sync:
            await self._sync_to_db(serial, updated_cache)
            self._last_sync_time[serial] = now

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
                            
                            if target_slot and tray_data:
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

