import asyncio
import os
import sys
from sqlmodel import select

# Add project root
sys.path.append(".")

from app.core.database import async_session_maker
from app.models.core import Printer

async def fix_printer():
    async with async_session_maker() as session:
        p = await session.get(Printer, "03919C461802608")
        if p:
            print(f"Printer: {p.name}")
            print(f"Status: {p.current_status}")
            print(f"Plate Cleared: {p.is_plate_cleared}")
            if not p.is_plate_cleared:
                print("FORCING is_plate_cleared = True")
                p.is_plate_cleared = True
                session.add(p)
                await session.commit()
                print("Updated successfully.")
        else:
            print("Printer not found.")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(fix_printer())
