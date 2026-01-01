import asyncio
import os
import sys
from sqlmodel import select

# Add project root
sys.path.append(".")

from app.core.database import async_session_maker
from app.models.core import Job

async def check_jobs():
    async with async_session_maker() as session:
        stmt = select(Job)
        jobs = (await session.exec(stmt)).all()
        print(f"Total Jobs: {len(jobs)}")
        for j in jobs:
            print(f"ID: {j.id}, Status: {j.status}, GCode: {repr(j.gcode_path)}")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_jobs())
