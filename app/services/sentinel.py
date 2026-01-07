import asyncio
import json
import logging
import ssl
import time
from typing import Dict, List, Optional, Any
from aiomqtt import Client, MqttError
import paho.mqtt.client as mqtt_base

from app.core.database import async_session_maker
from app.models.printer import Printer, PrinterState
from app.schemas.printer_cache import PrinterStateCache, AMSSlotCache
from app.core.redis import get_redis_client
from sqlalchemy import select

logger = logging.getLogger("PrinterSentinel")

# Stage Mapping for mc_print_stage
# 1: Printing, 2: Bed Leveling, 3: Heating, 4: XY Mech, 5: Filament Change, 
# 7: Paused, 8: Finished, 9: Busy, 10: Cleaning Nozzle, 11: Preparing, 12: Homing
STAGE_TO_STATUS = {
    1: PrinterState.PRINTING,
    2: PrinterState.PRINTING,
    3: PrinterState.PRINTING,
    4: PrinterState.PRINTING,
    5: PrinterState.PRINTING,
    6: PrinterState.PRINTING,
    7: PrinterState.PAUSED,
    8: PrinterState.AWAITING_CLEARANCE,
    9: PrinterState.PRINTING,
    10: PrinterState.PRINTING,
    11: PrinterState.PRINTING,
    12: PrinterState.PRINTING,
    13: PrinterState.PRINTING,
    14: PrinterState.PRINTING,
}

GCODE_STATE_TO_STATUS = {
    "IDLE": PrinterState.IDLE,
    "RUNNING": PrinterState.PRINTING,
    "FINISH": PrinterState.AWAITING_CLEARANCE,
    "PAUSE": PrinterState.PAUSED,
    "OFFLINE": PrinterState.OFFLINE,
}

class BambuMQTTClient:
    def __init__(self, serial: str, host: str, access_code: str):
        self.serial = serial
        self.host = host
        self.access_code = access_code
        self.running = True

    def _create_ssl_context(self) -> ssl.SSLContext:
        """STRICT implementation of Bambu SSL context."""
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context

    async def run(self):
        """Persistent connection loop with exponential backoff."""
        backoff = 1
        ssl_context = self._create_ssl_context()

        while self.running:
            try:
                logger.info(f"[{self.serial}] Connecting to {self.host}...")
                async with Client(
                    hostname=self.host,
                    port=8883,
                    username="bblp",
                    password=self.access_code,
                    tls_context=ssl_context,
                    protocol=mqtt_base.MQTTv311,
                    identifier=f"sentinel_{self.serial}",
                    keepalive=30,
                    timeout=30.0
                ) as client:
                    logger.info(f"[{self.serial}] Connected.")
                    backoff = 1 # Reset backoff on success
                    
                    topic = f"device/{self.serial}/report"
                    await client.subscribe(topic)
                    
                    async for message in client.messages:
                        try:
                            payload = json.loads(message.payload.decode())
                            await self._parse_and_cache(payload)
                        except json.JSONDecodeError:
                            logger.error(f"[{self.serial}] Invalid JSON payload")
                        except Exception as e:
                            logger.error(f"[{self.serial}] Processing error: {e}", exc_info=True)

            except MqttError as e:
                logger.warning(f"[{self.serial}] MQTT Error: {e}. Retrying in {backoff}s...")
            except Exception as e:
                logger.error(f"[{self.serial}] Unexpected error: {e}. Retrying in {backoff}s...")
            
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60) # Cap backoff at 60s

    async def _parse_and_cache(self, payload: dict):
        """Maps raw Bambu telemetry to PrinterStateCache and writes to Redis."""
        print_data = payload.get("print", {})
        if not print_data:
            return

        # 1. Determine Status
        mc_print_stage = print_data.get("mc_print_stage")
        gcode_state = print_data.get("gcode_state")
        
        status = PrinterState.IDLE
        if mc_print_stage in STAGE_TO_STATUS:
            status = STAGE_TO_STATUS[mc_print_stage]
        elif gcode_state in GCODE_STATE_TO_STATUS:
            status = GCODE_STATE_TO_STATUS[gcode_state]

        # 2. Extract AMS Data
        ams_cache_list = []
        ams_data = print_data.get("ams", {}).get("ams", [])
        for ams_unit in ams_data:
            ams_id = ams_unit.get("id", 0)
            trays = ams_unit.get("tray", [])
            for tray in trays:
                tray_id = tray.get("id", 0)
                global_slot_id = (int(ams_id) * 4) + int(tray_id)
                ams_cache_list.append(AMSSlotCache(
                    slot_id=global_slot_id,
                    color=tray.get("tray_color"),
                    material=tray.get("tray_type")
                ))

        # 3. Create Cache Model
        cache = PrinterStateCache(
            serial=self.serial,
            status=status,
            temps={
                "nozzle": float(print_data.get("nozzle_temper", 0.0)),
                "bed": float(print_data.get("bed_temper", 0.0))
            },
            progress=int(print_data.get("mc_percent", 0)),
            remaining_time_min=int(print_data.get("mc_remaining_time", 0)),
            active_file=print_data.get("subtask_name"),
            ams=ams_cache_list,
            updated_at=time.time()
        )

        # 4. Redis Write (60s TTL)
        redis = get_redis_client()
        key = f"printer:{self.serial}:status"
        await redis.set(key, cache.model_dump_json(), ex=60)

class SentinelManager:
    def __init__(self):
        self._clients: Dict[str, BambuMQTTClient] = {}
        self._tasks: List[asyncio.Task] = []

    async def start(self):
        """Initializes and starts all printer listeners."""
        logger.info("Initializing SentinelManager...")
        async with async_session_maker() as session:
            result = await session.execute(select(Printer))
            printers = result.scalars().all()
            
            for printer in printers:
                if not printer.ip_address or not printer.access_code:
                    logger.warning(f"Skipping printer {printer.serial}: Missing connection details.")
                    continue
                
                client = BambuMQTTClient(
                    serial=printer.serial,
                    host=printer.ip_address,
                    access_code=printer.access_code
                )
                self._clients[printer.serial] = client
                task = asyncio.create_task(client.run())
                self._tasks.append(task)
                logger.info(f"Sentinel task created for {printer.serial}")

    async def stop(self):
        """Gracefully shuts down all clients."""
        logger.info("Stopping SentinelManager...")
        for client in self._clients.values():
            client.running = False
        
        for task in self._tasks:
            task.cancel()
        
        await asyncio.gather(*self._tasks, return_exceptions=True)
        logger.info("SentinelManager stopped.")

if __name__ == "__main__":
    # For standalone testing
    async def main():
        manager = SentinelManager()
        await manager.start()
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            await manager.stop()

    asyncio.run(main())
