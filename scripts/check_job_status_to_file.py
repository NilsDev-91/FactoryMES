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
        with open("job_status_check.txt", "w", encoding="utf-8") as f:
            if job:
                f.write(f"ID: {job.id}\n")
                f.write(f"Status: {job.status}\n")
                f.write(f"Printer: {job.assigned_printer_serial}\n")
                f.write(f"Error: {job.error_message}\n")
                f.write(f"Filament Req: {job.filament_requirements}\n")
            else:
                f.write("No jobs found.\n")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_job())
