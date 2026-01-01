import asyncio
import os
import sys
from sqlmodel import select

# Add project root
sys.path.append(".")

from app.core.database import async_session_maker
from app.models.core import Printer

async def check():
    async with async_session_maker() as session:
        printer = await session.get(Printer, "03919C461802608")
        if printer:
            print(f"Status: {printer.current_status}")
            print(f"Plate Cleared: {printer.is_plate_cleared}")
        else:
            print("Printer not found.")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check())
