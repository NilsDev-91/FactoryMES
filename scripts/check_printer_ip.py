import asyncio
import sys
import os
sys.path.append(os.getcwd())
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

async def check():
    engine = create_async_engine(settings.ASYNC_DATABASE_URL)
    async with engine.connect() as conn:
        print("\n--- Printers IPs ---")
        result = await conn.execute(text("SELECT serial, name, ip_address, access_code FROM printers"))
        rows = result.fetchall()
        for row in rows:
            print(row)

if __name__ == "__main__":
    asyncio.run(check())
