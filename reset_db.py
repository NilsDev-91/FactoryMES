
import asyncio
from sqlalchemy import delete
from database import async_session_maker
from models import Printer, Job

async def clear_printers():
    async with async_session_maker() as session:
        print("Clearing 'jobs' table...")
        await session.execute(delete(Job))
        print("Clearing 'printers' table...")
        await session.execute(delete(Printer))
        await session.commit()
        print("Done.")

if __name__ == "__main__":
    asyncio.run(clear_printers())
