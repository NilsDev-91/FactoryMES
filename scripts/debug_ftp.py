import asyncio
import ssl
import aioftp
from sqlmodel import select
from app.core.database import async_session_maker
from app.models.core import Printer

async def debug_ftp():
    print("🕵️ Debugging functionality of Bambu FTP...")
    printer_serial = "03919C461802608"

    async with async_session_maker() as session:
        printer = await session.get(Printer, printer_serial)
        if not printer:
            print(f"❌ Printer {printer_serial} not found in DB.")
            return

    ip = printer.ip_address
    access_code = printer.access_code
    print(f"🖨️  Connecting to {ip} with code {access_code}...")

    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    async with aioftp.Client.context(
        host=ip,
        port=990,
        user="bblp",
        password=access_code,
        ssl=context
    ) as client:
        print("✅ Connected!")
        
        # 1. Check PWD
        print("\n--- PWD ---")
        try:
            pwd = await client.get_current_directory()
            print(f"Current Directory: {pwd}")
        except Exception as e:
            print(f"PWD Failed: {e}")

        # 2. List Root
        print("\n--- LIST . ---")
        try:
            files = await client.list()
            for path, info in files:
                print(f" - {path} ({info})")
        except Exception as e:
             print(f"LIST Failed: {e}")

        # 3. Test MKD (standard)
        print("\n--- TEST MKD /factoryos_debug ---")
        try:
            # Using raw command to see raw response if possible, 
            # but aioftp helper is easiest to test standard behavior logic code
            await client.make_directory("factoryos_debug")
            print("MKD 'factoryos_debug' Success")
        except Exception as e:
            print(f"MKD 'factoryos_debug' Failed: {e}")

        # 4. Test MKD with /sdcard prefix
        print("\n--- TEST MKD /sdcard/factoryos_debug ---")
        try:
            await client.make_directory("/sdcard/factoryos_debug")
            print("MKD '/sdcard/factoryos_debug' Success")
        except Exception as e:
            print(f"MKD '/sdcard/factoryos_debug' Failed: {e}")

        # 5. Clean up
        try:
            await client.remove_directory("factoryos_debug")
        except: pass
        try:
            await client.remove_directory("/sdcard/factoryos_debug")
        except: pass

if __name__ == "__main__":
    asyncio.run(debug_ftp())
