import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import select
from app.core.database import async_session_maker
from app.models.core import Job

async def check_job_errors():
    async with async_session_maker() as session:
        stmt = select(Job).where(Job.status == "FAILED")
        jobs = (await session.exec(stmt)).all()
        for j in jobs:
            print(f"Job {j.id} Failed: {j.error_message}")

if __name__ == "__main__":
    asyncio.run(check_job_errors())
