import asyncio
import sys
import os

# Add parent directory to path to allow importing database and models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import select, delete
from database import async_session_maker
from models import Printer

async def delete_dummies():
    async with async_session_maker() as session:
        # Find printers with "DUMMY" in serial or name
        stmt = select(Printer).where(Printer.serial.like("%DUMMY%"))
        result = await session.execute(stmt)
        dummies = result.scalars().all()
        
        print(f"Found {len(dummies)} dummy printers.")
        for p in dummies:
            print(f"Deleting {p.name} ({p.serial})")
            await session.delete(p)
            
        await session.commit()
        print("Deletion complete.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(delete_dummies())
