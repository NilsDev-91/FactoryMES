import asyncio
import json
import logging
import ssl
import time
from typing import Dict, Any, Optional, Tuple, List

import paho.mqtt.client as mqtt_base
from aiomqtt import Client, MqttError

# Core Infrastructure
from app.core.config import settings
from app.core.database import get_session
from app.core.redis import redis_client

# Service Layer (The Brains)
from app.services.filament_service import FilamentService
from app.services.job_executor import JobExecutionService

# Models
from app.models import Printer, PrinterState

logger = logging.getLogger("BambuMQTTWorker")

class BambuMQTTWorker:
    """
    High-Performance MQTT Worker for Bambu Lab printers.
    Acts as a non-blocking bridge between printers, Redis, and Postgres.
    """

    def __init__(self):
        self.queue = asyncio.Queue()
        self.redis = redis_client
        self._clients: Dict[str, Client] = {}
        self._last_state: Dict[str, str] = {} # Local memory cache for state tracking
        self._background_tasks = set()

    async def run(self, printers_config: List[Dict[str, str]]):
        """
        Starts the worker pipeline and printer listeners.
        """
        logger.info(f"Initializing BambuMQTTWorker for {len(printers_config)} printers.")
        
        # Start the consumer loop
        consumer_task = asyncio.create_task(self._process_message_queue())
        self._background_tasks.add(consumer_task)

        # Start listeners for each configured printer
        for cfg in printers_config:
            ip = cfg.get("ip")
            access_code = cfg.get("access_code")
            serial = cfg.get("serial")
            
            if not all([ip, access_code, serial]):
                logger.error(f"Incomplete config for printer: {cfg}")
                continue
                
            task = asyncio.create_task(self._run_client(ip, access_code, serial))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

        await asyncio.gather(*self._background_tasks, return_exceptions=True)

    async def _run_client(self, ip: str, access_code: str, serial: str):
        """
        Producer: Maintains connection to a single printer and pushes messages to the queue.
        """
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        while True:
            try:
                logger.debug(f"[{serial}] Connecting to {ip}...")
                async with Client(
                    hostname=ip,
                    port=8883,
                    username="bblp",
                    password=access_code,
                    tls_context=context,
                    protocol=mqtt_base.MQTTv311,
                    identifier=f"fOS_worker_{serial}",
                    keepalive=30,
                    timeout=30.0
                ) as client:
                    self._clients[serial] = client
                    logger.info(f"[{serial}] Connected successfully.")
                    
                    # Subscribe to report topic
                    await client.subscribe(f"device/{serial}/report")

                    async for message in client.messages:
                        await self.queue.put((serial, message.payload))
                        
            except MqttError as e:
                logger.warning(f"[{serial}] MQTT error: {e}. Reconnecting in 5s...")
            except Exception as e:
                logger.error(f"[{serial}] Client crash: {e}. Reconnecting in 5s...")
            
            self._clients.pop(serial, None)
            await asyncio.sleep(5)

    async def _process_message_queue(self):
        """
        Consumer: Processes incoming messages sequentially from the local queue.
        """
        logger.info("Message processing pipeline active.")
        while True:
            serial, payload = await self.queue.get()
            try:
                await self._handle_message(serial, payload)
            except Exception as e:
                logger.error(f"[{serial}] Error processing message: {e}", exc_info=True)
            finally:
                self.queue.task_done()

    async def _handle_message(self, serial: str, payload: Any):
        """
        Orchestrates the Hot/Cold path processing for a single payload.
        """
        try:
            if isinstance(payload, bytes):
                payload = payload.decode()
            data = json.loads(payload)
            
            print_data = data.get("print", {})
            if not print_data:
                return

            # --- Step A: Telemetry Caching (Redis - "The Hot Path") ---
            telemetry = {}
            # Map common Bambu keys
            mappings = {
                "nozzle_temper": "nozzle_temp",
                "bed_temper": "bed_temp",
                "mc_percent": "print_percentage",
                "wipe_state": "wiper_status",
                "layer_num": "layer_num"
            }
            
            for src, target in mappings.items():
                if src in print_data:
                    telemetry[target] = str(print_data[src])
            
            if telemetry:
                telemetry["updated_at"] = str(time.time())
                redis_key = f"printer:{serial}:telemetry"
                # Use a pipeline or direct hset for efficiency
                await self.redis.hset(redis_key, mapping=telemetry)
                await self.redis.expire(redis_key, 60) # Detect offline if no update for 60s

            # --- Step B: State Management (Postgres - "The Cold Path") ---
            new_state = print_data.get("gcode_state")
            if new_state:
                if new_state != self._last_state.get(serial):
                    logger.info(f"[{serial}] State Event: {self._last_state.get(serial)} -> {new_state}")
                    self._last_state[serial] = new_state
                    
                    async with get_session() as session:
                        executor = JobExecutionService(session)
                        await executor.handle_printer_state_change(serial, new_state)

            # --- Step C: AMS Events ---
            if "ams" in print_data:
                async with get_session() as session:
                    filament_service = FilamentService(session)
                    await filament_service.sync_ams_configuration(serial, print_data["ams"])

        except json.JSONDecodeError:
            logger.error(f"[{serial}] Received garbled JSON payload.")
        except Exception as e:
            raise e # Reraise to be caught by _process_message_queue for logging
