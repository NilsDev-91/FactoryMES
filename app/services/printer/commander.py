import os
import asyncio
import socket
import ssl
import json
import logging
import aioftp
from pathlib import Path
from typing import List, Optional
from aiomqtt import Client
import paho.mqtt.client as mqtt_base
from app.models.core import Printer, Job
from app.services.logic.file_processor import FileProcessorService

logger = logging.getLogger("PrinterCommander")


# DEBUG LOGGER
def debug_log(msg):
    with open("debug_commander.log", "a", encoding="utf-8") as f:
        import datetime
        f.write(f"[{datetime.datetime.now()}] {msg}\n")

class PrinterCommander:
    def __init__(self):
        logger.info("PrinterCommander Initialized (v2.1 - 3MF Sanitization Active + aiomqtt)")

    async def start_job(self, printer: Printer, job: Job, ams_mapping: List[int]) -> None:
        """
        High-level orchestrator to start a print job.
        1. Sanitizes the 3MF file (removes color metadata).
        2. Uploads sanitized file to printer via FTPS.
        3. Triggers print via MQTT.
        4. Cleans up temporary sanitized file.
        """
        if not printer.ip_address or not printer.access_code:
            raise ValueError(f"Printer {printer.serial} missing IP or Access Code")

        # Determine file path
        file_path = job.gcode_path
        if not file_path:
            product = getattr(job, "product", None)
            if product:
                file_path = product.file_path_3mf
        
        if not file_path:
            raise ValueError(f"No file path found for Job {job.id}")
            
        # Normalize Path
        file_path = file_path.replace("\\", "/")
        
        if not os.path.exists(file_path):
            logger.error(f"File not found on disk: {file_path}")
            raise FileNotFoundError(f"Source file missing: {file_path}")

        filename = file_path.split("/")[-1].split("\\")[-1]
        
        # Unique Remote Filename
        import time
        remote_filename = f"{filename.replace('.3mf', '')}_{int(time.time())}.3mf"

        sanitizer = FileProcessorService()
        sanitized_path: Optional[Path] = None
        
        try:
            # 1. Sanitize (T0 Master Protocol)
            # target_slot is 1-based (1-4). ams_index is 0-based (0-3).
            target_slot = ams_mapping[0]
            ams_index = max(0, target_slot - 1)

            logger.info(f"Sanitizing file for Job {job.id}: {file_path} -> T0 Master (Target: Slot {target_slot})")
            sanitized_path = await sanitizer.sanitize_and_repack(Path(file_path), target_index=ams_index, printer_type=printer.type)
            upload_source_path = str(sanitized_path)
            
            # T0 Master Mapping: Logical T0 -> Physical ams_index
            # We only need to map the first tool (index 0) because G-code only uses T0.
            final_mapping = [ams_index] 
            
            logger.info(f"Mapping Logical T0 -> Physical AMS Index {ams_index} (Slot {target_slot})")
            logger.info(f"Sanitized {filename} -> Uploading {remote_filename} with Mapping {final_mapping}")

            # 2. Upload File (With Retry)
            logger.info(f"Starting upload for Job {job.id} to {printer.serial}...")
            upload_success = False
            last_error = None
            for attempt in range(1, 4):
                try:
                    await self.upload_file(
                        ip=printer.ip_address, 
                        access_code=printer.access_code, 
                        local_path=upload_source_path, 
                        target_filename=remote_filename
                    )
                    upload_success = True
                    break
                except Exception as e:
                    last_error = e
                    logger.warning(f"Upload Attempt {attempt}/3 failed: {e}. Retrying in 2s...")
                    await asyncio.sleep(2)
            
            if not upload_success:
                 raise Exception(f"Upload Failed after 3 attempts: {last_error}") from last_error

            # 3. Start Print
            logger.info(f"Triggering MQTT print for Job {job.id} on {printer.serial}...")
            try:
                await self.start_print_job(
                    ip=printer.ip_address,
                    serial=printer.serial,
                    access_code=printer.access_code,
                    filename=remote_filename,
                    ams_mapping=final_mapping,
                    local_file_path=upload_source_path 
                )
            except Exception as e:
                raise Exception(f"MQTT Start Failed: {e}") from e
            
            logger.info(f"Job {job.id} started successfully on {printer.serial}")

        except Exception as e:
            logger.error(f"Failed to start Job {job.id} on {printer.serial}: {e}")
            raise e
        finally:
            # 4. Cleanup
            if sanitized_path and sanitized_path.exists():
                try:
                    sanitized_path.unlink()
                    logger.debug(f"Cleaned up temporary file: {sanitized_path}")
                except Exception as ex:
                    logger.warning(f"Failed to cleanup temp file {sanitized_path}: {ex}")

    async def upload_file(self, ip: str, access_code: str, local_path: str, target_filename: str) -> None:
        """
        Uploads a file to the printer via FTPS (Implicit TLS) using synchronous ftplib in a thread.
        This avoids aioftp/SSL issues on Windows.
        """
        # --- SIMULATION MODE ---
        if ip == "127.0.0.1":
            logger.info(f"SIMULATION: Mocking Upload to {ip}")
            await asyncio.sleep(1) 
            return
        # -----------------------

        logger.info(f"Uploading {local_path} to {ip} as {target_filename}...")
        debug_log(f"START UPLOAD (ftplib): {ip}, {target_filename}")

        def _sync_upload():
            import ftplib
            import ssl
            
            # Custom class for Implicit TLS
            class ImplicitFTP_TLS(ftplib.FTP_TLS):
                def __init__(self, host='', timeout=60):
                    super().__init__(host=host, timeout=timeout)
                    
                def connect(self, host='', port=0, timeout=-999):
                    if host != '':
                        self.host = host
                    if port > 0:
                        self.port = port
                    if timeout != -999:
                        self.timeout = timeout
                        
                    self.sock = socket.create_connection((self.host, self.port), self.timeout)
                    self.af = self.sock.family
                    
                    # IMPLICIT TLS: Wrap immediately
                    self.sock = self.context.wrap_socket(self.sock, server_hostname=self.host)
                    self.file = self.sock.makefile('r')
                    self.welcome = self.getresp()
                    return self.welcome

            try:
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                context.minimum_version = ssl.TLSVersion.TLSv1_2

                ftps = ImplicitFTP_TLS(timeout=30)
                ftps.context = context
                
                debug_log("Connecting (ftplib)...")
                ftps.connect(host=ip, port=990)
                debug_log("Connected! Logging in...")
                
                ftps.login(user="bblp", passwd=access_code)
                ftps.prot_p() # Secure data connection
                debug_log("Logged in. secure data channel (PBSZ 0, PROT P).")

                # FTP Root is usually the SD Card root on Bambu printers
                # So we upload to /factoryos, not /sdcard/factoryos
                target_dir = "/factoryos"
                
                # Check/Create Dir
                try:
                    ftps.mkd(target_dir)
                    debug_log(f"MKD {target_dir}")
                except Exception as e:
                     # Ignore if exists
                     debug_log(f"MKD ignored: {e}")
                
                ftps.cwd(target_dir)
                debug_log(f"CWD {target_dir}")
                
                debug_log(f"STOR {target_filename}")
                with open(local_path, "rb") as f:
                    try:
                        ftps.storbinary(f"STOR {target_filename}", f)
                    except TimeoutError as e:
                        # Bambu Printer sometimes times out on SSL Shutdown (unwrap)
                        # The file is usually transferred fine.
                        debug_log(f"WARNING: SSL Shutdown Timeout (Ignored): {e}")
                        logger.warning(f"FTPS Upload Shutdown Timeout: {e} (Assuming success)")
                    except ssl.SSLError as e:
                         # Handle "The read operation timed out" which sometimes comes as SSLError
                        if "timed out" in str(e):
                            debug_log(f"WARNING: SSL Shutdown Timeout/SSLError (Ignored): {e}")
                            logger.warning(f"FTPS Upload Shutdown SSLError: {e} (Assuming success)")
                        else:
                            raise e
                
                debug_log("Upload Complete (ftplib)")
                ftps.quit()
                
            except Exception as e:
                debug_log(f"FTPS Sync Error: {e}")
                raise e

        # Run in thread
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _sync_upload)
        logger.info(f"Upload to {ip} complete.")

    async def start_print_job(
        self, 
        ip: str, 
        serial: str, 
        access_code: str, 
        filename: str, 
        ams_mapping: List[int],
        local_file_path: Optional[str] = None
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
        
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        try:
            async with Client(
                hostname=ip,
                port=8883,
                username="bblp",
                password=access_code,
                tls_context=context,
                protocol=mqtt_base.MQTTv311, # FORCE 3.1.1
                identifier=f"commander_{serial}",
                timeout=30.0
            ) as client:
                
                logger.debug("MQTT Connected")
                
                topic = f"device/{serial}/request"
                
                # Determine Local IP for the URL param (placeholder logic)
                import socket
                try:
                    local_ip = socket.gethostbyname(socket.gethostname())
                except:
                    local_ip = "192.168.1.100"

                # Construct internal SD path (where upload_file put it)
                sd_path = f"/sdcard/factoryos/{filename}"
                
                # --- AUTO-DETECT GCODE PATH ---
                gcode_param = "Metadata/plate_1.gcode" # Default backup
                
                potential_paths = []
                if local_file_path:
                     potential_paths.append(local_file_path)
                
                potential_paths += [
                    f"storage/3mf/{filename}",
                    f"temp/{filename}",
                    filename
                ]
                
                found_local = None
                for p in potential_paths:
                    if os.path.exists(p):
                        found_local = p
                        break
                
                if found_local:
                    try:
                        import zipfile
                        with zipfile.ZipFile(found_local, 'r') as z:
                            for name in z.namelist():
                                if name.startswith("Metadata/") and name.endswith(".gcode"):
                                    gcode_param = name
                                    logger.info(f"Auto-detected GCode path: {gcode_param}")
                                    break
                    except Exception as e:
                        logger.warning(f"Failed to inspect 3MF for GCode path: {e}")
                else:
                     logger.warning(f"Could not find local file {filename} to verify GCode path. Using default.")

                # Payload matching Bambu Lab 3MF requirement
                payload = {
                    "print": {
                        "sequence_id": "2000",
                        "command": "project_file",
                        "param": gcode_param, 
                        "url": f"file:///sdcard/factoryos/{filename}", 
                        "md5": None,
                        "timelapse": False,
                        "bed_type": "auto", 
                        "bed_levelling": True,
                        "flow_cali": True,
                        "vibration_cali": True,
                        "layer_inspect": True,
                        "layer_inspect": True,
                        "use_ams": True,
                        # STRICTLY SINGLE ENTRY as per requirements for sanitized files
                        "ams_mapping": ams_mapping 
                    }
                }
                
                # Log as requested
                debug_log(f"MQTT PAYLOAD: {json.dumps(payload)}")
                logger.info(f"📡 SENDING MQTT CMD: {payload}")
                
                await client.publish(topic, json.dumps(payload))
                logger.info("Print payload published.")
                
                # Brief wait to ensure send
                await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error(f"MQTT Command Failed: {e}")
            raise e
