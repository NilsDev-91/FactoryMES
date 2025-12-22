
import asyncio
import json
import ssl
import logging
from ftplib import FTP_TLS
from typing import Optional, Callable, Dict, Any
import aiomqtt

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
        # SSL Context for self-signed certs
        tls_params = aiomqtt.TLSParameters(
            cert_reqs=ssl.CERT_NONE,
            tls_version=ssl.PROTOCOL_TLS,
            ciphers=None
        )

        while not self._stop_event.is_set():
            try:
                logger.info(f"Connecting to MQTT brokwer at {self.ip}...")
                async with aiomqtt.Client(
                    hostname=self.ip,
                    port=8883,
                    username="bblp",
                    password=self.access_code,
                    tls_params=tls_params,
                    identifier=f"factoryos-{self.serial}"
                ) as client:
                    self._mqtt_client = client
                    self.connected = True
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
                    logger.info("Sent push_status command")

                    async for message in client.messages:
                         await self._on_message(message)

            except aiomqtt.MqttError as e:
                self.connected = False
                logger.error(f"MQTT Connection error: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)
            except Exception as e:
                self.connected = False
                logger.error(f"Unexpected error: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)

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
            if "ams" in report: # AMS status is complex, just grabbing existence or basic info
                extracted["ams_status"] = "DETECTED" if report.get("ams") else "NONE"
            
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

    async def send_gcode_path(self, path: str):
        """Sends a request to start printing a file from the SD card."""
        if not self._mqtt_client or not self.connected:
            logger.error("Cannot send gcode: MQTT not connected")
            return

        # Command to start print (3mf/gcode needs to be on SD card)
        # Usually: {"print": {"command": "project_file", "param": "filename.gcode", ...}}
        # Or for specific gcode execution. 
        # Standard 'start print' from SD card file:
        payload = {
            "print": {
                "sequence_id": "0", # Optional but good practice
                "command": "project_file",
                "param": f"Metadata/{path}", # Often needs 'Metadata/' prefix or full path
                # Note: 'path' argument should probably be the full path on SD.
                # If path is just filename, might need prefix.
                # We will send 'path' as is if it looks absolute-ish or user provided.
            } 
        }
        
        # NOTE: 'project_file' is for 3mf. For raw .gcode, it might be different ("print_file"?)
        # Let's support the user's requirement: "send_gcode_path". 
        # If it's a .gcode file, we usually use:
        if path.endswith(".gcode"):
             payload = {
                "print": {
                    "command": "print",
                    "param": path # /sdcard/filename.gcode
                }
            }
        
        topic = f"device/{self.serial}/request"
        logger.info(f"Sending print request for {path} to {topic}")
        await self._mqtt_client.publish(topic, json.dumps(payload))

    async def upload_file(self, local_path: str, target_path: str, port: int = 990):
        """Uploads a file via FTPS (Implicit SSL). Runs in executor."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._upload_sync, local_path, target_path, port)

    def _upload_sync(self, local_path: str, target_path: str, port: int):
        """Blocking FTPS upload."""
        ftps = FTP_TLS()
        try:
            logger.info(f"Connecting to FTPS at {self.ip}:{port}...")
            ftps.connect(self.ip, port)
            ftps.login("bblp", self.access_code)
            ftps.prot_p() # Switch to secure data connection
            
            logger.info("Uploading file...")
            with open(local_path, "rb") as f:
                ftps.storbinary(f"STOR {target_path}", f)
            
            logger.info(f"Uploaded {local_path} to {target_path}")
        except Exception as e:
            logger.error(f"FTPS Upload error: {e}")
            raise
        finally:
            try:
                ftps.quit()
            except:
                pass

    def stop(self):
        self._stop_event.set()
