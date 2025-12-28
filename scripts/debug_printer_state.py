import asyncio
from sqlmodel import select
from app.core.database import async_session_maker
from app.models.core import Printer

async def check_printer_status():
    print("🔍 Checking Printer Status...")
    async with async_session_maker() as session:
        result = await session.exec(select(Printer))
        printers = result.all()
        for p in printers:
            print(f"🖨️  Printer: {p.name} (Serial: {p.serial})")
            print(f"    Status: {p.current_status}")
            print(f"    AMS Data: {p.ams_data}")
            print("-" * 30)

if __name__ == "__main__":
    asyncio.run(check_printer_status())
