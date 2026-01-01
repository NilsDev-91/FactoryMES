"""
Clear printer state and then try to start print with proper sequence
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

async def clear_and_start():
    async with async_session_maker() as session:
        printer = await session.get(Printer, "03919C461802608")
        if not printer:
            print("Printer not found.")
            return
        
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
                identifier=f"clear_start_{int(time.time())}",
                timeout=15.0
            ) as client:
                
                report_topic = f"device/{printer.serial}/report"
                await client.subscribe(report_topic)
                
                request_topic = f"device/{printer.serial}/request"
                
                # Step 1: Stop any current task
                print("Step 1: Sending stop command...")
                stop_payload = {
                    "print": {
                        "sequence_id": "1001",
                        "command": "stop"
                    }
                }
                await client.publish(request_topic, json.dumps(stop_payload))
                await asyncio.sleep(2)
                
                # Step 2: Clear the print variables
                print("Step 2: Cleaning...")
                clean_payload = {
                    "print": {
                        "sequence_id": "1002",
                        "command": "clean_print_error"
                    }
                }
                await client.publish(request_topic, json.dumps(clean_payload))
                await asyncio.sleep(1)
                
                # Step 3: Now send the project_file command
                print("Step 3: Starting print...")
                start_payload = {
                    "print": {
                        "sequence_id": "1003",
                        "command": "project_file",
                        "param": "Metadata/plate_1.gcode",
                        "url": "file:///sdcard/job_61.3mf",
                        "subtask_name": "job_61.3mf",
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
                await client.publish(request_topic, json.dumps(start_payload))
                
                # Wait for response
                print("\nWaiting for response...")
                start_time = time.time()
                async for message in client.messages:
                    if time.time() - start_time > 15:
                        break
                    
                    data = json.loads(message.payload.decode())
                    if "print" in data:
                        p = data["print"]
                        seq = p.get("sequence_id", "")
                        result = p.get("result", "")
                        reason = p.get("reason", "")
                        gcode_state = p.get("gcode_state", "")
                        gcode_file = p.get("gcode_file", "")
                        
                        if seq in ["1001", "1002", "1003"]:
                            print(f"[seq={seq}] result={result}, reason={reason}")
                        
                        if gcode_state and gcode_state != "IDLE":
                            print(f"\n*** PRINTER STATE CHANGED: {gcode_state} ***")
                            print(f"gcode_file: {gcode_file}")
                            break

        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(clear_and_start())
