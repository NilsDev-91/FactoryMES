import asyncio
import os
import sys
from sqlmodel import select

# Add project root
sys.path.append(".")

from app.core.database import async_session_maker
from app.models.core import Job

async def check_job():
    async with async_session_maker() as session:
        stmt = select(Job).order_by(Job.id.desc()).limit(1)
        job = (await session.exec(stmt)).first()
        if job:
            print(f"ID: {job.id}")
            print(f"Status: {job.status}")
            print(f"Printer: {job.assigned_printer_serial}")
            print(f"Error: {job.error_message}")
            print(f"Filament Req: {job.filament_requirements}")
        else:
            print("No jobs found.")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_job())
