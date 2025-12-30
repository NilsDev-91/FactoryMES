import asyncio
import sys
import os
sys.path.append(os.getcwd())
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.core.config import settings
from app.models.core import Job

async def check():
    engine = create_async_engine(settings.ASYNC_DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        jobs = (await session.exec(select(Job))).all()
        for job in jobs:
            print(f"Job {job.id}: Status={job.status}, Error={job.error_message}")

if __name__ == "__main__":
    asyncio.run(check())
