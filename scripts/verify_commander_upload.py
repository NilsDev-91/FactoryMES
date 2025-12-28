import asyncio
import logging
from app.services.printer.commander import PrinterCommander
from app.core.database import async_session_maker
from app.models.core import Printer

# Setup logging
logging.basicConfig(level=logging.INFO)

async def verify_upload():
    print("🧪 Verifying PrinterCommander Upload Fix...")
    printer_serial = "03919C461802608"

    async with async_session_maker() as session:
        printer = await session.get(Printer, printer_serial)
        if not printer:
            print("❌ Printer not found")
            return

    commander = PrinterCommander()
    
    # Use the dummy file we created earlier
    local_path = "storage/3mf/Eye_Master.3mf"
    filename = "Eye_Master_Test.3mf"

    try:
        await commander.upload_file(
            ip=printer.ip_address,
            access_code=printer.access_code,
            local_path=local_path,
            target_filename=filename
        )
        print("✅ Upload successful!")
    except Exception as e:
        print(f"❌ Upload failed: {e}")

if __name__ == "__main__":
    asyncio.run(verify_upload())
