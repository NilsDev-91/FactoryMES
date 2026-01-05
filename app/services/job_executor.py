import asyncio
import logging
import random
import json
import uuid
import ssl
import paho.mqtt.client as mqtt_base
from typing import Optional
from pathlib import Path
from aiomqtt import Client, MqttError

from app.core.database import async_session_maker
from app.services.job_dispatcher import job_dispatcher
from app.schemas.job import PartMetadata
from app.core.exceptions import StrategyNotApplicableError
from app.models.core import Printer, PrinterStatusEnum
from app.services.printer.kinematics import A1Kinematics
from app.services.logic.gcode_modifier import GCodeModifier
from app.services.logic.hms_parser import hms_parser

logger = logging.getLogger("JobExecutor")

class JobExecutor:
    """
    Phase 10: Production Job Executor
    Integrates the JobDispatcher into a resilient infinite loop.
    """
    A1_GANTRY_THRESHOLD_MM = 50.0

    def __init__(self):
        self.is_running = False

    def generate_a1_ejection(self, meta: PartMetadata) -> str:
        """
        Dispatches to the appropriate A1 ejection strategy based on part height.
        Protocol: A1 Gantry Sweep v1.2
        """
        if meta.height_mm >= self.A1_GANTRY_THRESHOLD_MM:
            logger.info(f"Part height {meta.height_mm}mm >= {self.A1_GANTRY_THRESHOLD_MM}mm -> Selected Strategy A: Gantry Sweep")
            return self._generate_a1_sweep_gcode(meta)
        else:
            logger.info(f"Part height {meta.height_mm}mm < {self.A1_GANTRY_THRESHOLD_MM}mm -> Selected Strategy B: Toolhead Push")
            return self._generate_a1_toolhead_push_gcode(meta)

    def _generate_a1_sweep_gcode(self, part_metadata: PartMetadata) -> str:
        """
        Strategy A: The Gantry Sweep (Height >= 50.0mm)
        Concept: Use the stationary X-Axis Gantry as a passive ram.
        Protocol: A1 Gantry Sweep v1.2
        """
        return f"""
; --- STRATEGY: A1_GANTRY_SWEEP (Gantry Beam) ---
; Protocol: A1 Gantry Sweep v1.2 | Height: {part_metadata.height_mm}mm

M84 S0 ; MOTOR LOCK: (Critical Safety)

; KINEMATICS
G90 ; Absolute Positioning
G1 X-13.5 F18000 ; Park Toolhead in cutter area (Clear path)
G1 Y256 F12000 ; Move Bed to Front (Setup Ram)
G1 Z4.0 F3000 ; Lower Z to Gantry Level (Beam Level)
M400
G1 Y0 F3000 ; SWEEP (Move Bed to Back)
M400

; RECOVERY
G1 Z10 F3000 ; Lift Z to reset
"""

    def _generate_a1_toolhead_push_gcode(self, meta: PartMetadata) -> str:
        """
        Strategy B: The Toolhead Push (Height < 50.0mm)
        Concept: Use the toolhead tip (nozzle) to actively push the part off.
        Protocol: A1 Gantry Sweep v1.2
        """
        return f"""
; --- STRATEGY: A1_TOOLHEAD_PUSH (Nozzle Tip) ---
; Protocol: A1 Gantry Sweep v1.2 | Height: {meta.height_mm}mm

M84 S0 ; MOTOR LOCK: (Critical Safety)
M104 S0 ; SAFETY: Turn off hotend immediately to prevent PEI damage

; KINEMATICS
G90 ; Absolute Positioning
G1 Z100 F3000 ; Lift Z for clearance
G1 X{meta.center_x} Y256 F12000 ; Position nozzle behind the part's X-center
G1 Z1.5 F3000 ; ENGAGE (Risk Zone)
M400
G1 Y0 F3000 ; PUSH (Move Bed Backward)
M400

; RECOVERY
G28 ; MANDATORY HOMING (Machine state restoration)
"""

    async def execute_monitored_sweep(self, printer: Printer, meta: PartMetadata):
        """
        Task 3: Active "Watchdog" Monitoring (Error Correction)
        Wraps the sweep in an asyncio monitor loop for auto-recovery.
        """
        logger.info(f"Starting MONITORED SWEEP for {printer.serial} (Part: {meta.height_mm}mm)")
        
        # 1. Generate & Seed G-code
        gcode = A1Kinematics.generate_a1_gantry_sweep_gcode(meta)
        gcode = GCodeModifier.inject_dynamic_seed(gcode)
        
        # 2. Execution with Retry Logic
        max_retries = 1
        current_attempt = 0
        
        while current_attempt <= max_retries:
            success = await self._run_sweep_cycle(printer, gcode, is_retry=(current_attempt > 0))
            if success:
                logger.info(f"Sweep SUCCESSFUL for {printer.serial} on attempt {current_attempt + 1}")
                return True
            
            current_attempt += 1
            if current_attempt <= max_retries:
                logger.warning(f"Sweep FAILED on {printer.serial}. Retrying once with auto-fix protocol...")
                # G-code modification for retry (Increased Torque)
                gcode = "M913 Y120 ; Increase Motor Current for Retry\n" + gcode
            
        logger.error(f"Sweep EXHAUSTED after {max_retries + 1} attempts on {printer.serial}. Manual intervention required.")
        return False

    async def _run_sweep_cycle(self, printer: Printer, gcode: str, is_retry: bool = False) -> bool:
        """
        Performs a single sweep cycle with active MQTT monitoring.
        """
        from app.services.printer.commander import PrinterCommander
        from app.services.production.bed_clearing_service import BedClearingService
        
        commander = PrinterCommander()
        clearing_service = BedClearingService()
        
        # Save G-code to temporary file for upload
        temp_path = Path(f"storage/temp/sweep_{printer.serial}_{uuid.uuid4().hex[:8]}.3mf")
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Package into 3MF
            maint_3mf_path = clearing_service.package_gcode_to_3mf(gcode, "sweep.gcode")
            
            # Start Watchdog Task
            watchdog_event = asyncio.Event()
            error_detected = {"state": False, "reason": None}
            
            # Subscribe & Listen
            monitor_task = asyncio.create_task(
                self._mqtt_watchdog(printer, watchdog_event, error_detected)
            )
            
            # Start Job
            logger.info(f"Uploading Sweep G-Code to {printer.serial} (Retry={is_retry})")
            await commander.start_maintenance_job(printer, maint_3mf_path)
            
            # Wait for completion OR error
            try:
                # We give the sweep 2 minutes max
                await asyncio.wait_for(watchdog_event.wait(), timeout=120)
            except asyncio.TimeoutError:
                logger.error(f"Sweep TIMEOUT on {printer.serial}. No completion event after 120s.")
                error_detected["state"] = True
                error_detected["reason"] = "Timeout"
            
            # Stop Watchdog
            monitor_task.cancel()
            
            if error_detected["state"]:
                logger.error(f"Watchdog Triggered: {error_detected['reason']} on {printer.serial}")
                # React: Abort current move
                await commander.send_printer_command(printer.serial, "CANCEL")
                await asyncio.sleep(5) # Cooldown
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Sweep Cycle Exception: {e}")
            return False
        finally:
            if 'maint_3mf_path' in locals() and maint_3mf_path.exists():
                maint_3mf_path.unlink()

    async def _mqtt_watchdog(self, printer: Printer, done_event: asyncio.Event, error_info: dict):
        """
        Internal MQTT listener for error detection during sweep.
        """
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        try:
            async with Client(
                hostname=printer.ip_address,
                port=8883,
                username="bblp",
                password=printer.access_code,
                tls_context=context,
                protocol=mqtt_base.MQTTv311,
                identifier=f"watchdog_{printer.serial}_{uuid.uuid4().hex[:4]}"
            ) as client:
                topic = f"device/{printer.serial}/report"
                await client.subscribe(topic)
                
                async for message in client.messages:
                    data = json.loads(message.payload).get("print", {})
                    
                    # 1. Detect Job Completion
                    gcode_state = data.get("gcode_state")
                    if gcode_state == "FINISH":
                        logger.info(f"Watchdog: Sweep FINISHED normally on {printer.serial}")
                        done_event.set()
                        return

                    # 2. Detect Errors (HMS codes)
                    hms_codes = data.get("hms", [])
                    if hms_codes:
                        events = hms_parser.parse(hms_codes)
                        for ev in events:
                            if "Stall" in ev.description or "Step Loss" in ev.description or "Collision" in ev.description:
                                error_info["state"] = True
                                error_info["reason"] = f"Mechanical Failure: {ev.description}"
                                done_event.set()
                                return
                    
                    # 3. Detect Generic Print Error
                    print_error = data.get("print_error", 0)
                    if print_error != 0:
                        error_info["state"] = True
                        error_info["reason"] = f"Print Error Code: {print_error}"
                        done_event.set()
                        return

        except Exception as e:
            logger.error(f"Watchdog MQTT Error: {e}")
            # Don't fail the whole sweep just because watchdog connection dropped, 
            # but ideally we should be robust.

    async def start(self):
        """Starts the autonomous production loop."""
        self.is_running = True
        logger.info("🚀 Autonomous Production Loop Started.")
        
        while self.is_running:
            try:
                await self.process_queue()
            except Exception as e:
                logger.error(f"Error in production loop: {e}", exc_info=True)
            
            # Frequency: Sleep for 5-10 seconds between cycles to avoid hammering DB/MQTT
            sleep_time = random.uniform(5, 10)
            await asyncio.sleep(sleep_time)

    async def stop(self):
        """Stops the loop."""
        self.is_running = False
        logger.info("🛑 Autonomous Production Loop Stopping...")

    async def process_queue(self):
        """
        Main execution logic.
        Strictly relies on the JobDispatcher to find the best match based on AMS telemetry.
        """
        async with async_session_maker() as session:
            # Inject the JobDispatcher matching logic
            await job_dispatcher.dispatch_next_job(session)

# Singleton
executor = JobExecutor()
