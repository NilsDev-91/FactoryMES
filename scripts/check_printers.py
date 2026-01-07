import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import select
from app.core.database import async_session_maker
from app.models.core import Printer

async def check_printers():
    async with async_session_maker() as session:
        stmt = select(Printer)
        printers = (await session.exec(stmt)).all()
        if not printers:
            print("No printers found in database.")
            return
        for p in printers:
            print(f"Printer: {p.serial} | Name: {p.name} | Status: {p.current_status} | Progress: {p.current_progress}%")

if __name__ == "__main__":
    asyncio.run(check_printers())
