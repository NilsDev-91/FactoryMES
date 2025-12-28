import asyncio
import logging
import ssl
import aioftp
from app.core.database import async_session_maker
from app.models.core import Printer

logging.basicConfig(level=logging.INFO)

async def verify_stream():
    print("🧪 Verifying upload_stream with standard file...")
    printer_serial = "03919C461802608"

    async with async_session_maker() as session:
        printer = await session.get(Printer, printer_serial)
        if not printer: return

    ip = printer.ip_address
    access_code = printer.access_code
    local_path = "storage/3mf/Eye_Master.3mf"
    filename = "Eye_Master_Stream.3mf"

    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    async with aioftp.Client.context(
        host=ip, port=990, user="bblp", password=access_code, ssl=context
    ) as client:
        
        print(f"Connected to {ip}")
        target_dir = "/sdcard/factoryos"
        
        # Manual CWD first
        try:
             await client.command(f"MKD {target_dir}", expected_codes=(250, 257))
        except: pass
        await client.change_directory(target_dir)

        print("Uploading via stream...")
        try:
            with open(local_path, "rb") as f:
                await client.upload_stream(f, filename)
            print("✅ Upload Stream Successful!")
        except Exception as e:
            print(f"❌ Upload Stream Failed: {e}")

if __name__ == "__main__":
    asyncio.run(verify_stream())
