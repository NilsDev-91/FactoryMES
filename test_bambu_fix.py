
import asyncio
import logging
import sys
from bambu_client import BambuPrinterClient

# Configure logging
logging.basicConfig(level=logging.INFO)

# Provided credentials
printer_ip = "192.168.2.213"
printer_access_code = "05956746"
printer_serial = "03919C461802608"

def on_update(data):
    logging.info(f"Received Update: {data}")

async def main():
    client = BambuPrinterClient(printer_ip, printer_access_code, printer_serial, update_callback=on_update)
    
    # Start MQTT connection in background
    task = asyncio.create_task(client.connect_mqtt())
    
    try:
        logging.info("Waiting for connection and updates...")
        await asyncio.sleep(10) # Run for 10 seconds to collect data
        
        if client.connected:
            logging.info("Successfully connected to printer via MQTT.")
        else:
            logging.warning("Could not connect to printer (might be offline or unreachable).")

    except KeyboardInterrupt:
        pass
    finally:
        client.stop()
        await task

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
