"""
Try starting print with gcode_file command (different from project_file)
Some Bambu printers use gcode_file for already-uploaded files
"""
import asyncio
import os
import sys
import ssl
import json
import time
from aiomqtt import Client
import paho.mqtt.client as mqtt_base

sys.path.append(".")

from app.core.database import async_session_maker
from app.models.core import Printer

async def start_print():
    async with async_session_maker() as session:
        printer = await session.get(Printer, "03919C461802608")
        if not printer:
            print("Printer not found.")
            return
        
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        # The file that exists on the printer
        existing_file = "2feceedf-9dc7-4a65-8650-c76b99782f3a_1767280913.3mf"
        
        try:
            async with Client(
                hostname=printer.ip_address,
                port=8883,
                username="bblp",
                password=printer.access_code,
                tls_context=context,
                protocol=mqtt_base.MQTTv311,
                identifier=f"start_print_{int(time.time())}",
                timeout=15.0
            ) as client:
                
                report_topic = f"device/{printer.serial}/report"
                await client.subscribe(report_topic)
                
                request_topic = f"device/{printer.serial}/request"
                
                # Try the gcode_file approach
                payload = {
                    "print": {
                        "sequence_id": "99999",
                        "command": "gcode_file",
                        "param": f"/{existing_file}",
                        "print_type": "local"
                    }
                }
                
                print(f"Sending gcode_file command:")
                print(json.dumps(payload, indent=2))
                
                await client.publish(request_topic, json.dumps(payload))
                
                print("\nWaiting for response...")
                start_time = time.time()
                async for message in client.messages:
                    if time.time() - start_time > 10:
                        break
                    
                    data = json.loads(message.payload.decode())
                    if "print" in data:
                        p = data["print"]
                        seq = p.get("sequence_id", "")
                        result = p.get("result", "")
                        reason = p.get("reason", "")
                        gcode_state = p.get("gcode_state", "")
                        
                        if seq == "99999" or gcode_state:
                            print(f"\nResponse: result={result}, reason={reason}, gcode_state={gcode_state}")
                            if gcode_state and gcode_state != "IDLE":
                                print(f"*** PRINTER IS NOW: {gcode_state} ***")
                                break
                                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(start_print())
