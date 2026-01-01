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

async def monitor_printer():
    output = []
    async with async_session_maker() as session:
        printer = await session.get(Printer, "03919C461802608")
        if not printer:
            output.append("Printer not found.")
        else:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
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
                    identifier=f"monitor_full_{printer.serial}_{int(time.time())}",
                    timeout=10.0
                ) as client:
                    
                    topic = f"device/{printer.serial}/report"
                    await client.subscribe(topic)
                    
                    # Request full status
                    payload = {"print": {"command": "push_status", "sequence_id": "1"}}
                    await client.publish(f"device/{printer.serial}/request", json.dumps(payload))
                    
                    output.append("Waiting for full telemetry...")
                    
                    msg_count = 0
                    async for message in client.messages:
                        data = json.loads(message.payload.decode())
                        output.append(f"\n--- Message {msg_count} ---")
                        output.append(json.dumps(data, indent=2))
                        msg_count += 1
                        if msg_count >= 3: # Capture a few to be sure
                            break
            except Exception as e:
                output.append(f"MQTT Monitor Failed: {e}")

    with open("telemetry_full_dump.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output))

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(monitor_printer())
