"""
Extended telemetry capture after print command to check gcode_state
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

async def capture_state():
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
                identifier=f"state_check_{int(time.time())}",
                timeout=10.0
            ) as client:
                
                report_topic = f"device/{printer.serial}/report"
                await client.subscribe(report_topic)
                
                # Request full status
                request_topic = f"device/{printer.serial}/request"
                await client.publish(request_topic, json.dumps({
                    "pushing": {"sequence_id": "1", "command": "pushall"}
                }))
                
                print("Waiting for full status report...")
                
                start_time = time.time()
                async for message in client.messages:
                    if time.time() - start_time > 15:
                        break
                    
                    data = json.loads(message.payload.decode())
                    if "print" in data:
                        p = data["print"]
                        # Check for important fields
                        gcode_state = p.get("gcode_state")
                        subtask_name = p.get("subtask_name")
                        mc_print_stage = p.get("mc_print_stage")
                        print_error = p.get("print_error")
                        stg_cur = p.get("stg_cur")
                        
                        if gcode_state or mc_print_stage or print_error:
                            print(f"\n=== Status Report ===")
                            print(f"gcode_state: {gcode_state}")
                            print(f"subtask_name: {subtask_name}")
                            print(f"mc_print_stage: {mc_print_stage}")
                            print(f"print_error: {print_error}")
                            print(f"stg_cur: {stg_cur}")
                            
                            # Save full message
                            with open("full_status.txt", "w", encoding="utf-8") as f:
                                f.write(json.dumps(data, indent=2))
                            print("Saved full status to full_status.txt")
                            break
                            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(capture_state())
