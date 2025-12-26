import asyncio
import json
import ssl
import socket
import logging
from ftplib import FTP_TLS
from typing import Optional, Callable, Dict, Any
import aiomqtt

class ImplicitFTP_TLS(FTP_TLS):
    """
    FTP_TLS subclass that supports Implicit SSL (Port 990).
    Wraps the socket in SSL immediately upon connection.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def connect(self, host='', port=0, timeout=-999):
        if host != '':
            self.host = host
        if port > 0:
            self.port = port
        if timeout != -999:
            self.timeout = timeout
            
        # Create standard socket
        self.sock = socket.create_connection((self.host, self.port), self.timeout)
        self.af = self.sock.family
        
        # Wrap it in SSL immediately (Implicit Mode)
        # We use a permissive context for self-signed certs
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        self.sock = ctx.wrap_socket(self.sock, server_hostname=self.host)
        
        # Resume standard connect process (get welcome msg)
        self.file = self.sock.makefile('r', encoding=self.encoding)
        self.welcome = self.getresp()
        return self.welcome 

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BambuClient")

class BambuPrinterClient:
    def __init__(self, ip: str, access_code: str, serial: str, update_callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.ip = ip
        self.access_code = access_code
        self.serial = serial
        self.update_callback = update_callback
        self.connected = False
        self._mqtt_client: Optional[aiomqtt.Client] = None
        self._stop_event = asyncio.Event()

    async def connect_mqtt(self):
        """Connects to the printer's MQTT broker with auto-reconnect."""
        # SSL Context for self-signed certs (Optimized for Bambu)
        tls_params = aiomqtt.TLSParameters(
            cert_reqs=ssl.CERT_NONE,
            tls_version=ssl.PROTOCOL_TLSv1_2,
            ciphers=None
        )

        # Exponential Backoff variables
        retry_delay = 1
        max_delay = 30
        
        self.last_message_time = 0.0

        while not self._stop_event.is_set():
            try:
                # Debug Logging for Connection Details
                logger.info(f"Connecting to MQTT broker at {self.ip}:8883...")
                logger.debug(f"SSL Params: Version={tls_params.tls_version}, CertReqs={tls_params.cert_reqs}")
                
                async with aiomqtt.Client(
                    hostname=self.ip,
                    port=8883,
                    username="bblp",
                    password=self.access_code,
                    tls_params=tls_params,
                    identifier=f"factoryos-{self.serial}",
                    keepalive=45,     # Increased from 10s to 45s for stability
                    timeout=30        # Explicit connection timeout (30s)
                ) as client:
                    self._mqtt_client = client
                    self.connected = True
                    retry_delay = 1 # Reset backoff on success
                    logger.info("MQTT Connected!")

                    # Subscribe to report topic
                    full_topic = f"device/{self.serial}/report"
                    await client.subscribe(full_topic)
                    logger.info(f"Subscribed to {full_topic}")

                    # Request status update (Enable pushing)
                    push_cmd = {
                        "pushing": {
                            "sequence_id": "0",
                            "command": "start"
                        }
                    }
                    await client.publish(f"device/{self.serial}/request", json.dumps(push_cmd))
                    
                    # Watchdog Loop
                    # We run the message loop, but if it exits or errors, we catch it.
                    async for message in client.messages:
                         self.last_message_time = asyncio.get_running_loop().time()
                         await self._on_message(message)

            except aiomqtt.MqttError as e:
                self.connected = False
                logger.error(f"MQTT Connection error: {e}. Reconnecting in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_delay)
                
            except Exception as e:
                self.connected = False
                logger.error(f"Unexpected error: {e}. Reconnecting in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_delay)

    async def _on_message(self, message: aiomqtt.Message):
        """Handles incoming MQTT messages."""
        try:
            payload = message.payload
            if isinstance(payload, bytes):
               payload = payload.decode()
            
            data = json.loads(payload)
            # Extract relevant fields
            # The structure of Bambu reports is typically wrapped in 'print' or 'print_type'
            # We look for specific keys in the nested naming structure if needed, or flat.
            # Usually it comes as {"print": {"command": "push_status", ...}} or just flat fields depending on firmware.
            # We'll try to find keys recursively or checking known locations.
            
            report = data.get("print", {})
            if not report and "print" not in data: 
                 # Sometimes it's directly in root if not a push_status wrapper? 
                 # But typically it is inside "print". Let's assume standard structure.
                 report = data
            
            logger.info(f"Report Keys: {list(report.keys())}")
            if "gcode_state" in report:
                logger.info(f"Gcode State: {report['gcode_state']}")
            
            extracted = {}
            if "gcode_state" in report:
                extracted["print_status"] = report.get("gcode_state")
            if "nozzle_temper" in report:
                extracted["nozzle_temper"] = report.get("nozzle_temper")
            if "bed_temper" in report:
                extracted["bed_temper"] = report.get("bed_temper")
            
            # --- AMS Parsing ---
            # Structure: print.ams.ams[0].tray[0...3]
            # Each tray has: { "id": "0", "cols": ["FF0000"], "tray_type": "PLA", ... }
            if "ams" in report and "ams" in report["ams"]:
                ams_list = report["ams"]["ams"]
                if ams_list and len(ams_list) > 0:
                    trays = ams_list[0].get("tray", [])
                    parsed_ams = []
                    for t in trays:
                        # Bambu colors are often 8 hex chars (RRGGBB + Alpha/padded?), usually we want last 6
                        raw_color = t.get("tray_color", "000000") # Start simple
                        # If generic color provided
                        
                        filament_type = t.get("tray_type", "Unknown")
                        # remaining might not be in basic report, but we'll look for it
                        
                        parsed_ams.append({
                            "slot": t.get("id"),
                            "color": f"#{raw_color[:6]}", # Assuming standard hex format
                            "type": filament_type,
                            "remaining": t.get("remain", -1), # -1 = Unknown/Generic (Assume full/available) # Percentage?
                        })
                    
                    extracted["ams_data"] = parsed_ams

            # Additional fields commonly needed
            if "mc_percent" in report:
                extracted["progress"] = report.get("mc_percent")
            if "mc_remaining_time" in report:
                extracted["remaining_time"] = report.get("mc_remaining_time")

            if extracted and self.update_callback:
                self.update_callback(extracted)

        except json.JSONDecodeError:
            logger.warning("Received invalid JSON payload")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def send_gcode_path(self, path: str, ams_mapping: list = None):
        """
        Sends a request to start printing a file from the SD card.
        :param path: Full path on SD (e.g., /filename.3mf)
        :param ams_mapping: List of AMS slot indices corresponding to objects in 3mf (e.g. [2])
        """
        if not self._mqtt_client or not self.connected:
            logger.error("Cannot send gcode: MQTT not connected")
            return

        # Clean path: Remove 'Metadata/' if present to avoid duplication
        # Bambu A1 usually wants just the filename or path relative to SD root for 'project_file'
        # BUT 'param' field behavior varies. 
        # Safest: If it starts with slash, treat as absolute.
        cleaned_path = path.lstrip('/')
        
        # Command Structure for 3MF
        payload = {
            "print": {
                "sequence_id": "0",
                "command": "project_file",
                "param": f"file:///sdcard/{cleaned_path}", # Correct param for 3MF seems to be the full file URL or just filename?
                # Actually, some docs say param: "Metadata/plate_1.gcode" IF it's unzipped.
                # BUT if it is a single .3mf file, we might need:
                # 'param': f'file:///sdcard/{cleaned_path}' ?
                # Let's try matching URL and Param or just filename.
                # Standard P1P/X1C 3MF print:
                # command: "project_file"
                # param: "Metadata/plate_1.gcode" <-- This implies the printer unzips it?
                # url: "file:///sdcard/filename.3mf"
                
                # WAIT. If we upload a .3mf, does the printer unzip it automatically?
                # Usually YES for X1/P1.
                # If so, the "param" must point to the GCODE INSIDE the 3mf.
                # Typically inside a 3MF, the gcode is at "Metadata/plate_1.gcode".
                
                # So my previous code was: "param": f"Metadata/{cleaned_path}"
                # If cleaned_path is "file.3mf", then param became "Metadata/file.3mf". THIS IS WRONG.
                # It should be "Metadata/plate_1.gcode" (default) or we need to look inside the 3mf to find the gcode name.
                
                # Let's assume standard Bambu Studio export which uses "Metadata/plate_1.gcode".
                "param": "Metadata/plate_1.gcode", 
                
                "url": f"file:///sdcard/{cleaned_path}",
                "plate_id": 1,
                "use_ams": True if ams_mapping else False,
                "ams_mapping": ams_mapping if ams_mapping else [0],
                "bed_type": "auto",
                "timelapse": False,
            } 
        }
        
        # For simple .gcode (older way)
        if path.endswith(".gcode"):
             payload = {
                "print": {
                    "command": "print",
                    "param": f"file:///sdcard/{cleaned_path}"
                }
            }
        
        topic = f"device/{self.serial}/request"
        logger.info(f"Sending print request for {cleaned_path} to {topic} with AMS {ams_mapping}")
        await self._mqtt_client.publish(topic, json.dumps(payload))

    async def upload_file(self, local_path: str, target_path: str, port: int = 990):
        """Uploads a file via FTPS (Implicit SSL). Runs in executor."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._upload_sync, local_path, target_path, port)

    def _upload_sync(self, local_path: str, target_path: str, port: int):
        """Blocking FTPS upload using system curl for stability."""
        import subprocess
        
        # Use implicit FTPS (port 990)
        # curl -k --ftp-ssl -u user:pass -T local remote_url
        # target_path starts with /, so we construct url carefully
        # URL: ftps://IP:990/path
        
        remote_url = f"ftps://{self.ip}:{port}{target_path}"
        
        cmd = [
            "curl.exe",
            "-k",               # Insecure (Self-signed)
            "--ftp-ssl",        # SSL/TLS
            "-u", f"bblp:{self.access_code}",
            "-T", local_path,
            remote_url
        ]
        
        logger.info(f"Uploading via curl: {remote_url}")
        try:
            # Capture output to log on error
            result = subprocess.run(
                cmd, 
                check=True, 
                capture_output=True, 
                text=True,
                timeout=300 # 5 minutes timeout
            )
            # logger.debug(result.stderr) # Curl writes progress/stats to stderr
            logger.info(f"Uploaded {local_path} to {target_path} successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Curl Upload Failed: {e.stderr}")
            raise Exception(f"Curl failed with exit code {e.returncode}: {e.stderr}")
        except subprocess.TimeoutExpired:
             logger.error("Curl Upload Timed Out")
             raise Exception("Upload timed out")
        except FileNotFoundError:
            logger.error("curl.exe not found in PATH")
            raise Exception("curl.exe not found. Please install curl or ensure it is in PATH.")


    def stop(self):
        self._stop_event.set()
