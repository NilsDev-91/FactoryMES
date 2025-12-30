
import asyncio
import ssl
import json
import logging
import aioftp
from typing import List, Optional
from gmqtt import Client as MQTTClient
from app.models.core import Printer, Job

logger = logging.getLogger("PrinterCommander")

class PrinterCommander:
    def __init__(self):
        pass

    async def start_job(self, printer: Printer, job: Job, ams_mapping: List[int]) -> None:
        """
        High-level orchestrator to start a print job.
        1. Uploads GCode/3MF to printer via FTPS.
        2. Triggers print via MQTT if upload succeeds.
        """
        if not printer.ip_address or not printer.access_code:
            raise ValueError(f"Printer {printer.serial} missing IP or Access Code")

        # Determine file path
        # Prefer specific job path, fallback to product path
        file_path = job.gcode_path
        if not file_path:
            # Try getting from product if lazy loaded or available
            product = getattr(job, "product", None)
            if product:
                file_path = product.file_path_3mf
        
        if not file_path:
            raise ValueError(f"No file path found for Job {job.id}")

        filename = file_path.split("/")[-1].split("\\")[-1]

        try:
            # 1. Upload File
            logger.info(f"Starting upload for Job {job.id} to {printer.serial}...")
            await self.upload_file(
                ip=printer.ip_address, 
                access_code=printer.access_code, 
                local_path=file_path, 
                target_filename=filename
            )

            # 2. Start Print
            logger.info(f"Triggering MQTT print for Job {job.id} on {printer.serial}...")
            await self.start_print_job(
                ip=printer.ip_address,
                serial=printer.serial,
                access_code=printer.access_code,
                filename=filename,
                ams_mapping=ams_mapping
            )
            
            logger.info(f"Job {job.id} started successfully on {printer.serial}")

        except Exception as e:
            logger.error(f"Failed to start Job {job.id} on {printer.serial}: {e}")
            raise e

    async def upload_file(self, ip: str, access_code: str, local_path: str, target_filename: str) -> None:
        """
        Uploads a file to the printer via FTPS (Implicit TLS).
        Uploads to /sdcard/factoryos/.
        """
        # --- SIMULATION MODE ---
        if ip == "127.0.0.1":
            logger.info(f"SIMULATION: Mocking Upload to {ip}")
            await asyncio.sleep(1) # Simulate network delay
            return
        # -----------------------

        logger.info(f"Uploading {local_path} to {ip} as {target_filename}...")
        
        # Configure SSL for Implicit TLS (Port 990)
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        try:
            async with aioftp.Client.context(
                host=ip,
                port=990,
                user="bblp",
                password=access_code,
                ssl=context,
                socket_timeout=10,
                path_timeout=10
            ) as client:
                
                # Check/Create directory
                target_dir = "/sdcard/factoryos"
                try:
                    # Bambu Printer returns 250 for MKD, standard is 257.
                    # We manually send command to accept both.
                    await client.command(f"MKD {target_dir}", expected_codes=(250, 257))
                except aioftp.StatusCodeError as e:
                    # 550 usually means directory already exists (or permission denied)
                    # We can ignore 550 and try CWD.
                    if "550" not in str(e):
                        logger.warning(f"MKD failed with unexpected error: {e}")

                # Change directory
                await client.change_directory(target_dir)
                
                # Upload
                # write_into=True suppresses internal make_directory call which fails on Bambu (250 vs 257)
                await client.upload(local_path, target_filename, write_into=True)
                logger.info(f"Upload to {ip} complete.")
                
        except Exception as e:
            logger.error(f"FTPS Upload Failed: {e}")
            raise e

    async def start_print_job(
        self, 
        ip: str, 
        serial: str, 
        access_code: str, 
        filename: str, 
        ams_mapping: List[int]
    ) -> None:
        """
        Connects to MQTT, sends print command, and disconnects.
        """
        # --- SIMULATION MODE ---
        if ip == "127.0.0.1":
            logger.info(f"SIMULATION: Mocking MQTT Command to {ip}")
            await asyncio.sleep(0.5)
            return
        # -----------------------

        logger.info(f"Sending Print Command to {serial} ({ip})...")
        
        client = MQTTClient(client_id=f"commander_{serial}")
        client.set_auth_credentials("bblp", access_code)
        
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        connected_event = asyncio.Event()
        
        def on_connect(client, flags, rc, properties):
            logger.debug("MQTT Connected")
            connected_event.set()
            
        client.on_connect = on_connect
        
        try:
            await client.connect(ip, 8883, ssl=context)
            await _async_wait(connected_event) # Wait for connection
            
            topic = f"device/{serial}/request"
            
            # Determine Local IP for the URL param (placeholder logic)
            # In production, get this from os.environ or socket
            import socket
            try:
                # get host ip (rough approximation)
                local_ip = socket.gethostbyname(socket.gethostname())
            except:
                local_ip = "192.168.1.100"

            # Construct internal SD path (where upload_file put it)
            # upload_file uses /sdcard/factoryos/
            sd_path = f"/sdcard/factoryos/{filename}"
            
            # Payload matching Bambu Lab 3MF requirement
            payload = {
                "print": {
                    "command": "project_file",
                    "sequence_id": "2000",
                    "param": sd_path, 
                    "url": f"http://{local_ip}:9000/api/files/{filename}", 
                    "md5": None,
                    "ams_mapping": ams_mapping,
                    "use_ams": True
                }
            }
            
            # Log as requested
            logger.info(f"📡 SENDING MQTT CMD: {payload}")
            
            client.publish(topic, json.dumps(payload))
            logger.info("Print payload published.")
            
            # Brief wait to ensure send
            await asyncio.sleep(0.5)
            
            await client.disconnect()
            
        except Exception as e:
            logger.error(f"MQTT Command Failed: {e}")
            raise e

# Helper for waiting
async def _async_wait(event: asyncio.Event, timeout=10):
    try:
        await asyncio.wait_for(event.wait(), timeout)
    except asyncio.TimeoutError:
         raise TimeoutError("MQTT Connection Timeout")
