import os
import time
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
    try:
        log_dir = Path("temp")
        log_dir.mkdir(exist_ok=True)
        log_path = log_dir / "debug_commander.log"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"{msg}\n")
    except:
        pass

class PrinterCommander:
    def __init__(self):
        logger.info("PrinterCommander Initialized (v2.2 - 3MF Sanitization + Calibration Jogging)")

    async def send_raw_gcode(self, printer: Printer, gcode_lines: List[str]) -> None:
        """Sends a raw G-code sequence to the printer via MQTT."""
        if not printer.ip_address or not printer.access_code:
            raise ValueError(f"Printer {printer.serial} missing IP or Access Code")

        gcode_text = "\n".join(gcode_lines)
        logger.info(f"Sending Raw G-Code to {printer.serial}: {gcode_lines}")
        
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
                identifier=f"cmd_raw_{printer.serial}",
                timeout=10.0
            ) as client:
                topic = f"device/{printer.serial}/request"
                payload = {
                    "print": {
                        "sequence_id": str(int(time.time() % 10000)),
                        "command": "gcode_line",
                        "param": gcode_text + "\n"
                    }
                }
                await client.publish(topic, json.dumps(payload))
                await asyncio.sleep(0.2)
        except Exception as e:
            logger.error(f"Failed to send raw G-code to {printer.serial}: {e}")
            raise e

    async def jog_axis(self, printer: Printer, axis: str, distance: float, speed: int = 1500) -> None:
        """Jogs a specific axis by a distance using relative positioning."""
        axis = axis.upper()
        if axis not in ["X", "Y", "Z"]:
            raise ValueError(f"Invalid axis: {axis}")

        gcode = [
            "G91",                  # Relative positioning
            f"G1 {axis}{distance} F{speed}",
            "G90"                   # Restore absolute positioning
        ]
        await self.send_raw_gcode(printer, gcode)


    async def start_job(self, printer: Printer, job: Job, ams_mapping: List[int], is_calibration_due: bool = True, part_height_mm: Optional[float] = None) -> None:
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
        
        # Unique Remote Filename - SIMPLIFIED for A1 firmware compatibility
        # A1 firmware ignores/corrupts commands with long filenames containing GUIDs
        remote_filename = f"job_{job.id}.3mf"

        sanitizer = FileProcessorService()
        sanitized_path: Optional[Path] = None
        
        try:
            # 1. Sanitize (T0 Master Protocol)
            # target_index is 0-based for the sanitizer (0-3). ams_mapping[0] is 1-based (1-4).
            ams_index = max(0, ams_mapping[0] - 1)

            # Extract filament requirements for metadata matching
            # Format: [{"material": "...", "hex_color": "..."}]
            req_color = "#FFFFFF"
            req_material = "PLA"
            if job.filament_requirements and len(job.filament_requirements) > 0:
                req = job.filament_requirements[0]
                req_color = req.get("hex_color") or req.get("color") or "#FFFFFF"
                req_material = req.get("material") or "PLA"

            logger.info(f"Sanitizing file for Job {job.id}: {file_path} -> T{ams_index} (Target Color: {req_color})")
            logger.info(f"Dynamic Calibration: Due={is_calibration_due}")
            
            result = await sanitizer.sanitize_and_repack(
                Path(file_path), 
                target_index=ams_index, 
                filament_color=req_color,
                filament_type=req_material,
                printer_type=printer.type, 
                is_calibration_due=is_calibration_due,
                part_height_mm=part_height_mm
            )
            sanitized_path = result.file_path
            upload_source_path = str(sanitized_path)
            
            # Native Strategy: Identity Mapping
            # We explicitly call T{ams_index} in G-code, so ams_mapping must be 1:1.
            final_mapping = [0, 1, 2, 3]
            
            logger.info(f"Job {job.id} sanitized. Auto-Eject Active: {result.is_auto_eject_enabled} (Height: {result.detected_height}mm)")
            logger.info(f"Targeting Physical AMS Index {ams_index} (Slot {ams_index + 1}) via Native G-Code Injection.")
            
            # 2. Upload File (With Retry)
            if not os.path.exists(upload_source_path):
                logger.error(f"Sanitized file missing before upload: {upload_source_path}")
                raise FileNotFoundError(f"Sanitized file deleted unexpectedly: {upload_source_path}")

            logger.info(f"Starting upload for Job {job.id} to {printer.serial} (File: {upload_source_path})...")
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
                    local_file_path=upload_source_path,
                    use_calibration=is_calibration_due
                )
            except Exception as e:
                raise Exception(f"MQTT Start Failed: {e}") from e
            
            logger.info(f"Job {job.id} started successfully on {printer.serial}")
            return result

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

    async def start_maintenance_job(self, printer: Printer, local_3mf_path: Path) -> None:
        """
        Specialized method for maintenance tasks (like bed clearing).
        Uploads and starts a 3MF file without sanitization.
        """
        if not printer.ip_address or not printer.access_code:
            raise ValueError(f"Printer {printer.serial} missing IP or Access Code")

        filename = local_3mf_path.name
        # Unique Remote Filename
        import time
        remote_filename = f"maint_{int(time.time())}_{filename}"

        try:
            # 1. Upload
            logger.info(f"Uploading maintenance job to {printer.serial}: {remote_filename}")
            await self.upload_file(
                ip=printer.ip_address,
                access_code=printer.access_code,
                local_path=str(local_3mf_path),
                target_filename=remote_filename
            )

            # 2. Trigger Print
            mapping = [0, 1, 2, 3]
            logger.info(f"Triggering maintenance job on {printer.serial}...")
            await self.start_print_job(
                ip=printer.ip_address,
                serial=printer.serial,
                access_code=printer.access_code,
                filename=remote_filename,
                ams_mapping=mapping,
                local_file_path=str(local_3mf_path)
            )
            
            logger.info(f"Maintenance Job {remote_filename} started successfully.")

        except Exception as e:
            logger.error(f"Maintenance Job Failed for {printer.serial}: {e}")
            raise e

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
        
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Source file for upload missing: {local_path}")
            
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

                # FTP Root is the SD Card on Bambu printers
                # Upload directly to root to avoid path confusion
                target_dir = "/"
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
        local_file_path: Optional[str] = None,
        use_calibration: bool = True
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

        logger.info(f"Sending Print Command to {serial} ({ip})... (Calibration={use_calibration})")
        
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

                # Use the filename provided by the caller (already includes the job ID from start_job)
                sd_url = f"file:///sdcard/{filename}"
                
                # ams_mapping MUST be a 16-element array for Bambu A1
                # Normalizing 1-based DB slots (1-4) to 0-based HW slots (0-3)
                full_ams_mapping = [-1] * 16
                if ams_mapping:
                    for i, slot_val in enumerate(ams_mapping):
                        if i < 16 and slot_val is not None:
                            # ams_mapping values are already 0-indexed hardware IDs (0-15)
                            full_ams_mapping[i] = slot_val
                
                # --- AUTO-DETECT GCODE PATH & MD5 ---
                gcode_param = "Metadata/plate_1.gcode" 
                md5_val = None
                
                check_path = local_file_path if local_file_path and os.path.exists(local_file_path) else None
                
                if check_path:
                    try:
                        import hashlib
                        with open(check_path, "rb") as f:
                            md5_val = hashlib.md5(f.read()).hexdigest()
                            
                        import zipfile
                        with zipfile.ZipFile(check_path, 'r') as z:
                            # Prefer plate_1.gcode
                            if "Metadata/plate_1.gcode" in z.namelist():
                                gcode_param = "Metadata/plate_1.gcode"
                            else:
                                for name in z.namelist():
                                    if name.startswith("Metadata/") and name.endswith(".gcode"):
                                        gcode_param = name
                                        break
                        logger.info(f"A1 Protocol: MD5={md5_val} | GCode={gcode_param}")
                    except Exception as e:
                        logger.warning(f"Failed to inspect asset for A1 protocol: {e}")

                # Payload matching Bambu Lab 3MF requirement
                # For local SD card prints, these IDs should be "0"
                payload = {
                    "print": {
                        "sequence_id": str(int(time.time() % 10000)),
                        "command": "project_file",
                        "param": gcode_param, 
                        "url": sd_url,
                        "subtask_name": filename,
                        "md5": md5_val if md5_val else "",
                        "file": "",
                        "profile_id": "0",
                        "project_id": "0",
                        "subtask_id": "0",
                        "task_id": "0",
                        "timelapse": False,
                        "bed_type": "auto", 
                        "bed_levelling": use_calibration,
                        "flow_cali": use_calibration,
                        "vibration_cali": use_calibration,
                        "layer_inspect": True,
                        "use_ams": True,
                        "ams_mapping": full_ams_mapping 
                    }
                }
                
                # Log as requested
                debug_log(f"MQTT PAYLOAD: {json.dumps(payload)}")
                logger.info(f"📡 SENDING MQTT CMD: project_file {filename} (Tools 0-3 -> Slots 0-3)")
                
                await client.publish(topic, json.dumps(payload))
                logger.info("Print payload published.")
                
                # Brief wait to ensure send
                await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error(f"MQTT Command Failed: {e}")
            raise e
