
import asyncio
from app.core.database import async_session_maker
from app.models.core import Job, JobStatusEnum
from sqlalchemy import select

async def check():
    async with async_session_maker() as session:
        stmt = select(Job).where(Job.id.in_([28, 29, 30]))
        jobs = (await session.execute(stmt)).scalars().all()
        for j in jobs:
            print(f"Job {j.id}: {j.status} (assigned to {j.assigned_printer_serial})")

if __name__ == "__main__":
    asyncio.run(check())
