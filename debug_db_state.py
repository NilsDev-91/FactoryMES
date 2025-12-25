
import asyncio
import sys
from sqlmodel import select
from database import async_session_maker
from models import Printer, Job

async def debug_db():
    async with async_session_maker() as session:
        print("--- PRINTERS ---")
        result = await session.execute(select(Printer))
        for p in result.scalars().all():
            print(f"Serial: {p.serial}, Status: {p.current_status}")

        print("\n--- JOBS ---")
        result = await session.execute(select(Job))
        for j in result.scalars().all():
            print(f"Job ID: {j.id}, Status: {j.status}, Assigned: {j.assigned_printer_serial}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(debug_db())
