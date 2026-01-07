
import os
import time
import asyncio
import ssl
import json
import logging
import hashlib
from pathlib import Path
from typing import List, Optional, Any, Dict
import aioftp
import aiomqtt
import paho.mqtt.client as mqtt_base
from app.core.exceptions import PrinterNetworkError

logger = logging.getLogger("PrinterCommander")

class PrinterCommander:
    """
    Robust, non-blocking communication layer for Bambu Lab printers.
    Instantiated per printer to maintain credential context.
    Uses FTPS (Implicit TLS) for uploads and MQTT for control.
    """

    def __init__(self, ip: str, access_code: str, serial: str):
        """
        Initializes the commander with printer credentials.
        
        Args:
            ip: Printer's LAN IP address.
            access_code: Printer's 8-character access code.
            serial: Printer's serial number.
        """
        self.ip = ip
        self.access_code = access_code
        self.serial = serial
        
        # Shared SSL Context for FTPS and MQTT
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    async def upload_file_async(self, local_path: Path, target_path: str = "/") -> str:
        """
        Uploads a file to the printer via FTPS (Implicit TLS on Port 990).
        Uses aioftp for non-blocking I/O.
        
        Args:
            local_path: Path to the local .3mf or .gcode file.
            target_path: Remote directory on SD card (default root "/").
            
        Returns:
            str: The full path to the file on the printer (e.g., "/sdcard/job.3mf").
            
        Raises:
            PrinterNetworkError: If upload fails due to network or authentication issues.
        """
        if not local_path.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")

        filename = local_path.name
        remote_filename = f"{target_path.rstrip('/')}/{filename}".replace("//", "/")
        
        logger.info(f"[{self.serial}] Starting async upload: {filename} -> {self.ip}")
        
        try:
            # Bambu Implicit TLS is mandatory on port 990
            async with aioftp.Client.context(
                self.ip,
                port=990,
                user="bblp",
                password=self.access_code,
                ssl=self.ssl_context,
                socket_timeout=30.0
            ) as client:
                await client.upload(local_path, remote_filename)
                
            logger.info(f"[{self.serial}] Upload completed successfully.")
            
            # Bambu expects /sdcard/ prefix in the URL field for project_file command
            return f"/sdcard{remote_filename}"
            
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
            logger.error(f"[{self.serial}] Network error during upload: {e}")
            raise PrinterNetworkError(self.serial, f"Connection failed: {str(e)}")
        except Exception as e:
            logger.error(f"[{self.serial}] Unexpected upload failure: {e}")
            raise PrinterNetworkError(self.serial, f"Upload failed: {str(e)}")

    async def start_print_job(
        self, 
        file_path_on_printer: str, 
        ams_mapping: List[int],
        md5_sum: Optional[str] = None,
        gcode_param: str = "Metadata/plate_1.gcode",
        use_calibration: bool = True
    ) -> None:
        """
        Publishes the MQTT payload to start a print job.
        
        Args:
            file_path_on_printer: Full path on SD card (e.g., /sdcard/test.3mf).
            ams_mapping: 16-element array of hardware IDs (0-15, or -1).
            md5_sum: Optional MD5 of the file for verification.
            gcode_param: Entry point inside the 3MF (default Metadata/plate_1.gcode).
            use_calibration: Whether to enable leveling/cali.
        """
        # Ensure mapping is exactly 16 elements
        mapping_payload = [-1] * 16
        for i, val in enumerate(ams_mapping):
            if i < 16:
                mapping_payload[i] = val

        payload = {
            "print": {
                "sequence_id": str(int(time.time() % 10000)),
                "command": "project_file",
                "param": gcode_param,
                "url": f"file://{file_path_on_printer}",
                "subtask_name": Path(file_path_on_printer).name,
                "md5": md5_sum or "",
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
                "ams_mapping": mapping_payload
            }
        }

        topic = f"device/{self.serial}/request"
        logger.info(f"[{self.serial}] Publishing MQTT Print Start...")
        
        try:
            async with aiomqtt.Client(
                hostname=self.ip,
                port=8883,
                username="bblp",
                password=self.access_code,
                tls_context=self.ssl_context,
                protocol=mqtt_base.MQTTv311,
                timeout=10.0
            ) as client:
                await client.publish(topic, json.dumps(payload))
                
            logger.info(f"[{self.serial}] Print command published.")
            
        except Exception as e:
            logger.error(f"[{self.serial}] MQTT Command Failed: {e}")
            raise PrinterNetworkError(self.serial, f"MQTT publish failed: {str(e)}")

    async def send_raw_gcode(self, gcode_line: str) -> None:
        """Sends a single G-code line or sequence via MQTT."""
        payload = {
            "print": {
                "sequence_id": str(int(time.time() % 10000)),
                "command": "gcode_line",
                "param": gcode_line + "\n"
            }
        }
        topic = f"device/{self.serial}/request"
        try:
            async with aiomqtt.Client(
                hostname=self.ip,
                port=8883,
                username="bblp",
                password=self.access_code,
                tls_context=self.ssl_context,
                protocol=mqtt_base.MQTTv311,
                timeout=10.0
            ) as client:
                await client.publish(topic, json.dumps(payload))
        except Exception as e:
            raise PrinterNetworkError(self.serial, str(e))

    async def send_printer_command(self, command: str) -> None:
        """Sends a simple control command (e.g., 'stop', 'pause', 'resume')."""
        payload = {
            "print": {
                "sequence_id": str(int(time.time() % 10000)),
                "command": command.lower()
            }
        }
        topic = f"device/{self.serial}/request"
        try:
            async with aiomqtt.Client(
                hostname=self.ip,
                port=8883,
                username="bblp",
                password=self.access_code,
                tls_context=self.ssl_context,
                protocol=mqtt_base.MQTTv311,
                timeout=10.0
            ) as client:
                await client.publish(topic, json.dumps(payload))
        except Exception as e:
            raise PrinterNetworkError(self.serial, str(e))
