import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def check_printers():
    database_url = settings.ASYNC_DATABASE_URL
    engine = create_async_engine(database_url)
    
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT serial, name, ip_address, access_code FROM printers"))
        printers = res.fetchall()
        
        if not printers:
            print("No printers found in database.")
            return
            
        for p in printers:
            print(f"Serial: {p.serial}, Name: {p.name}, IP: {p.ip_address}, Access Code: {'***' if p.access_code else 'Missing'}")
        
    await engine.dispose()

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_printers())
