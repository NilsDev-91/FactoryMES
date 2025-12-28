import asyncio
import json
import logging
import ssl
from typing import Optional
import aiomqtt
from sqlmodel import select
from app.core.database import async_session_maker
from app.models.core import Printer, PrinterStatusEnum
from app.models.filament import AmsSlot

logger = logging.getLogger(__name__)

class PrinterMqttWorker:
    def __init__(self, settings):
        self.settings = settings
        self.retry_interval = 10  # seconds

    async def start_listening(self, printer_ip: str, access_code: str, serial: str):
        """
        Starts the MQTT listener loop for a specific printer.
        """
        topic = f"device/{serial}/report"
        
        # TLS configuration for Bambu Lab printers (self-signed certs)
        tls_params = aiomqtt.TLSParameters(
            tls_version=ssl.PROTOCOL_TLS,
            cert_reqs=ssl.CERT_NONE
        )

        logger.info(f"Starting MQTT worker for printer {serial} at {printer_ip}")

        while True:
            try:
                async with aiomqtt.Client(
                    hostname=printer_ip,
                    port=8883,
                    username="bblp",
                    password=access_code,
                    tls_params=tls_params,
                    timeout=5
                ) as client:
                    logger.info(f"Connected to printer {serial} at {printer_ip}")
                    await client.subscribe(topic)
                    async for message in client.messages:
                        await self._handle_message(serial, message.payload)
            except aiomqtt.MqttError as e:
                logger.error(f"MQTT error for printer {serial}: {e}. Retrying in {self.retry_interval}s...")
                await asyncio.sleep(self.retry_interval)
            except Exception as e:
                logger.error(f"Unexpected error for printer {serial}: {e}. Retrying in {self.retry_interval}s...")
                await asyncio.sleep(self.retry_interval)

    async def _handle_message(self, serial: str, payload: bytes):
        try:
            data = json.loads(payload)
            # Bambu Lab MQTT payload structure: {"print": {...}}
            print_data = data.get("print")
            if not print_data:
                return

            # Extract fields
            nozzle_temp = print_data.get("nozzle_temper")
            bed_temp = print_data.get("bed_temper")
            gcode_state = print_data.get("gcode_state") # IDLE, RUNNING, PAUSE, FINISH, FAILED
            mc_percent = print_data.get("mc_percent")
            
            # Map gcode_state to PrinterStatusEnum
            status = None
            if gcode_state == "RUNNING":
                status = PrinterStatusEnum.PRINTING
            elif gcode_state in ["FINISH", "FAILED", "IDLE"]:
                status = PrinterStatusEnum.IDLE
            
            async with async_session_maker() as session:
                statement = select(Printer).where(Printer.serial == serial)
                result = await session.exec(statement)
                printer = result.one_or_none()
                
                if printer:
                    if nozzle_temp is not None:
                        printer.current_temp_nozzle = float(nozzle_temp)
                    if bed_temp is not None:
                        printer.current_temp_bed = float(bed_temp)
                    if status is not None:
                        printer.current_status = status
                    if mc_percent is not None:
                        printer.current_progress = int(mc_percent)
                    
                    session.add(printer)
                    
                    # Handle AMS Data
                    ams_obj = print_data.get("ams")
                    if ams_obj and "ams" in ams_obj:
                        ams_list = ams_obj["ams"]
                        for ams_idx, ams_unit in enumerate(ams_list):
                            trays = ams_unit.get("tray", [])
                            for slot_idx, tray in enumerate(trays):
                                tray_color = tray.get("tray_color")
                                tray_type = tray.get("tray_type")
                                remain = tray.get("remain")
                                
                                # Upsert AmsSlot
                                ams_slot_stmt = select(AmsSlot).where(
                                    AmsSlot.printer_id == serial,
                                    AmsSlot.ams_index == ams_idx,
                                    AmsSlot.slot_index == slot_idx
                                )
                                ams_slot_result = await session.exec(ams_slot_stmt)
                                ams_slot = ams_slot_result.one_or_none()
                                
                                if not ams_slot:
                                    ams_slot = AmsSlot(
                                        printer_id=serial,
                                        ams_index=ams_idx,
                                        slot_index=slot_idx,
                                        tray_color=tray_color,
                                        tray_type=tray_type,
                                        remaining_percent=remain
                                    )
                                else:
                                    ams_slot.tray_color = tray_color
                                    ams_slot.tray_type = tray_type
                                    ams_slot.remaining_percent = remain
                                
                                session.add(ams_slot)

                    await session.commit()
                    logger.debug(f"Updated printer {serial} telemetry (including AMS)")
        except json.JSONDecodeError:
            logger.error(f"Failed to decode MQTT payload for printer {serial}")
        except Exception as e:
            logger.error(f"Error handling message for printer {serial}: {e}")
