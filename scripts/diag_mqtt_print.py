"""
Direct MQTT Print Command Test with Response Capture
This script bypasses the normal flow and directly sends a print command,
then captures the printer's response to understand any rejection.
"""
import asyncio
import os
import sys
import ssl
import json
import time
import hashlib
from aiomqtt import Client
import paho.mqtt.client as mqtt_base

sys.path.append(".")

from app.core.database import async_session_maker
from app.models.core import Printer

async def test_print_command():
    results = []
    
    async with async_session_maker() as session:
        printer = await session.get(Printer, "03919C461802608")
        if not printer:
            print("Printer not found.")
            return
        
        print(f"Testing direct MQTT command to {printer.serial} at {printer.ip_address}")
        
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
                identifier=f"diag_print_{int(time.time())}",
                timeout=15.0
            ) as client:
                
                # Subscribe to receive responses
                report_topic = f"device/{printer.serial}/report"
                await client.subscribe(report_topic)
                print(f"Subscribed to {report_topic}")
                
                # Build the payload - using the simplest possible version
                # Based on Bambu Studio's local print command
                payload = {
                    "print": {
                        "sequence_id": "12345",
                        "command": "project_file",
                        "param": "Metadata/plate_1.gcode",
                        "url": "file:///sdcard/2feceedf-9dc7-4a65-8650-c76b99782f3a_1767280913.3mf",
                        "subtask_name": "test_print.3mf",
                        "md5": "",
                        "file": "",
                        "profile_id": "0",
                        "project_id": "0",
                        "subtask_id": "0",
                        "task_id": "0",
                        "timelapse": False,
                        "bed_type": "auto",
                        "bed_levelling": True,
                        "flow_cali": True,
                        "vibration_cali": True,
                        "layer_inspect": False,
                        "use_ams": True,
                        "ams_mapping": [0, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1]
                    }
                }
                
                request_topic = f"device/{printer.serial}/request"
                print(f"\nSending to {request_topic}:")
                print(json.dumps(payload, indent=2))
                
                await client.publish(request_topic, json.dumps(payload))
                print("\n--- Waiting for response (10 seconds) ---")
                
                start_time = time.time()
                msg_count = 0
                
                async for message in client.messages:
                    elapsed = time.time() - start_time
                    if elapsed > 10:
                        break
                    
                    data = json.loads(message.payload.decode())
                    results.append(data)
                    
                    # Check for specific response types
                    if "print" in data:
                        p = data["print"]
                        seq_id = p.get("sequence_id", "")
                        result = p.get("result", "")
                        reason = p.get("reason", "")
                        gcode_state = p.get("gcode_state", "")
                        
                        if seq_id == "12345" or result or reason:
                            print(f"\n*** RESPONSE [{elapsed:.1f}s] ***")
                            print(f"  sequence_id: {seq_id}")
                            print(f"  result: {result}")
                            print(f"  reason: {reason}")
                            print(f"  gcode_state: {gcode_state}")
                        elif gcode_state:
                            print(f"[{elapsed:.1f}s] gcode_state: {gcode_state}")
                    
                    msg_count += 1
                    if msg_count >= 20:
                        break
                        
        except Exception as e:
            print(f"Error: {e}")
    
    # Save all results
    with open("mqtt_response_log.txt", "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, indent=2) + "\n\n")
    print(f"\nSaved {len(results)} messages to mqtt_response_log.txt")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_print_command())
