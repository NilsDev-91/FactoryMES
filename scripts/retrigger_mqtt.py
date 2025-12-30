import asyncio
import os
import sys
import logging
import json
import ssl
from gmqtt import Client as MQTTClient

# Ensure app modules are found
sys.path.append(os.getcwd())

logging.basicConfig(level=logging.DEBUG)

IP = "192.168.2.213"
SERIAL = "03919C461802608"
ACCESS_CODE = "05956746"
FILENAME = "debug_prot_c.3mf"
AMS_MAPPING = [1, 1, 1, 1]  # Broadcast to Slot 2 (Black)

async def test_mqtt_trigger():
    print(f"Triggering Print via MQTT for {FILENAME}...")
    
    client = MQTTClient(client_id=f"debugger_{SERIAL}")
    client.set_auth_credentials("bblp", ACCESS_CODE)
    
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    
    connected_event = asyncio.Event()
    
    def on_connect(client, flags, rc, properties):
        print("✅ MQTT Connected")
        connected_event.set()
        
    client.on_connect = on_connect
    
    try:
        await client.connect(IP, 8883, ssl=context)
        await asyncio.wait_for(connected_event.wait(), timeout=10)
        
        topic = f"device/{SERIAL}/request"
        
        # CORRECTED PAYLOAD (Metadata/plate_3.gcode)
        payload = {
            "print": {
                "sequence_id": "3001",
                "command": "project_file",
                "param": f"Metadata/plate_3.gcode", 
                "url": f"file:///sdcard/factoryos/{FILENAME}", 
                "md5": None,
                "timelapse": False,
                "bed_type": "auto", 
                "bed_levelling": True,
                "flow_cali": True,
                "vibration_cali": True,
                "layer_inspect": True,
                "use_ams": True, 
                "ams_mapping": AMS_MAPPING,
                "subtask_name": "Pro Test Job"
            }
        }
        
        print(f"📡 Sending Payload: {json.dumps(payload)}")
        client.publish(topic, json.dumps(payload))
        
        await asyncio.sleep(2) # Give it time to send
        await client.disconnect()
        print("✅ Command Sent. Check Printer.")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_mqtt_trigger())
