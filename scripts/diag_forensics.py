import asyncio
import os
import sys
import ssl
import json
import time
from aiomqtt import Client
import paho.mqtt.client as mqtt_base

# Add project root
sys.path.append(".")

from app.core.database import async_session_maker
from app.models.core import Printer

async def capture_forensics():
    output = []
    async with async_session_maker() as session:
        printer = await session.get(Printer, "03919C461802608")
        if not printer:
            print("Printer not found.")
            return

        print(f"Starting 30s Forensics Capture for {printer.serial}...")
        
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
                identifier=f"forensics_{printer.serial}_{int(time.time())}",
                timeout=10.0
            ) as client:
                
                topic = f"device/{printer.serial}/report"
                await client.subscribe(topic)
                
                # Request a full status refresh
                request_topic = f"device/{printer.serial}/request"
                payload = {"print": {"command": "push_status", "sequence_id": "1"}}
                await client.publish(request_topic, json.dumps(payload))
                
                start_time = time.time()
                msg_count = 0
                
                async for message in client.messages:
                    if time.time() - start_time > 30:
                        break
                        
                    data = json.loads(message.payload.decode())
                    output.append(f"\n[{time.time():.2f}] --- Message {msg_count} ---")
                    output.append(json.dumps(data, indent=2))
                    msg_count += 1
                    
        except Exception as e:
            output.append(f"\nMQTT Error: {e}")

    with open("telemetry_forensics.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output))
    print(f"Capture complete. Logged {len(output)} lines to telemetry_forensics.txt")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(capture_forensics())
