import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import select
from app.core.database import async_session_maker
from app.models.core import Printer

async def check_ams():
    async with async_session_maker() as session:
        stmt = select(Printer)
        printers = (await session.exec(stmt)).all()
        for p in printers:
            print(f"Printer: {p.serial} | AMS Data: {p.ams_data}")

if __name__ == "__main__":
    asyncio.run(check_ams())
