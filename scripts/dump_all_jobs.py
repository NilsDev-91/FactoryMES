import asyncio
import os
import sys
from sqlmodel import select

# Add project root
sys.path.append(".")

from app.core.database import async_session_maker
from app.models.core import Job

async def dump_jobs():
    async with async_session_maker() as session:
        stmt = select(Job)
        jobs = (await session.exec(stmt)).all()
        with open("all_jobs_dump.txt", "w", encoding="utf-8") as f:
            f.write(f"Total Jobs: {len(jobs)}\n")
            for j in jobs:
                f.write(f"ID: {j.id}, Status: {j.status}, GCode: {repr(j.gcode_path)}, Req: {j.filament_requirements}\n")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(dump_jobs())
