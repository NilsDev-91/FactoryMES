import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker
from sqlalchemy import text

async def check():
    async with async_session_maker() as session:
        res = (await session.execute(text('SELECT serial, name, current_status, is_plate_cleared FROM printers'))).all()
        for r in res:
            print(f"RAW: {r}")

if __name__ == "__main__":
    asyncio.run(check())
