import os
import sys
import json
import ssl
import random
import time
import logging
from typing import Optional

# Add project root to path for SQLModel and settings
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    import paho.mqtt.client as mqtt
    from sqlmodel import Session, select, create_engine
    from app.core.config import settings
    from app.models.core import Printer
except ImportError as e:
    print(f"Error: Missing dependencies. Ensure sqlmodel, paho-mqtt, and app modules are available. {e}")
    sys.exit(1)

# Diagnostic Configuration
TARGET_SERIAL = "03919C461802608"
CLIENT_ID = f"fms-monitor-{random.randint(100, 999)}"

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("AMSMonitor")

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"✅ Connected to Printer {TARGET_SERIAL} (ID: {CLIENT_ID})")
        topic = f"device/{TARGET_SERIAL}/report"
        client.subscribe(topic)
        print(f"📡 Subscribed to {topic}")
        print("⏳ Waiting for telemetry (move a spool or wait for heartbeat)...")
    else:
        print(f"❌ Connection failed with result code {rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        
        # Bambu telemetry is usually under the 'print' key
        print_data = payload.get("print")
        if not print_data:
            return

        # Check for AMS data
        ams_root = print_data.get("ams")
        if ams_root and "ams" in ams_root:
            ams_list = ams_root["ams"]
            
            clear_console()
            print("=" * 60)
            print(f"  LIVE AMS MONITOR - {TARGET_SERIAL}")
            print(f"  Timestamp: {time.strftime('%H:%M:%S')}")
            print("=" * 60)
            print(f"{'Slot':<8} | {'Material':<10} | {'Color':<10} | {'RFID (Detected)'}")
            print("-" * 60)

            for ams_idx, ams_unit in enumerate(ams_list):
                trays = ams_unit.get("tray", [])
                for tray_idx, tray in enumerate(trays):
                    slot_num = (ams_idx * 4) + tray_idx + 1
                    
                    if not tray:
                        print(f"Slot {slot_num:<3} | {'EMPTY':<10} | {'-':<10} | -")
                        continue

                    material = tray.get("tray_type", "Unknown")
                    color = tray.get("tray_color", "#??????")
                    # Note: Bambu doesn't always expose raw RFID string directly in 'report', 
                    # but tray_sub_brands/tag_uid might be present in some firmwares or detailed reports.
                    rfid_info = tray.get("tag_uid", "No RFID Tag")
                    
                    print(f"Slot {slot_num:<3} | {material:<10} | {color:<10} | {rfid_info}")
            
            print("-" * 60)
            print(" (Ctrl+C to stop)")
        else:
            # Minimal heartbeat indicator
            sys.stdout.write(".")
            sys.stdout.flush()

    except Exception as e:
        logger.error(f"Error parsing message: {e}")

def run_monitor():
    # 1. Fetch Credentials from DB
    engine = create_engine(settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://"))
    
    with Session(engine) as session:
        statement = select(Printer).where(Printer.serial == TARGET_SERIAL)
        printer = session.exec(statement).first()
        
        if not printer:
            print(f"❌ Error: Printer {TARGET_SERIAL} not found in database.")
            return
        
        if not printer.ip_address or not printer.access_code:
            print(f"❌ Error: Printer {TARGET_SERIAL} is missing IP or Access Code.")
            return

        ip = printer.ip_address
        access_code = printer.access_code

    # 2. Setup MQTT Client
    client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
    client.username_pw_set("bblp", access_code)
    
    # 3. Setup SSL (Bambu Specific)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_v1_2)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    client.tls_set_context(context)

    client.on_connect = on_connect
    client.on_message = on_message

    print(f"🔌 Connecting to {ip}:8883...")
    try:
        client.connect(ip, 8883, keepalive=60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped.")
    except Exception as e:
        print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    run_monitor()
