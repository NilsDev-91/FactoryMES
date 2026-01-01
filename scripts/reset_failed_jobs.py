
import asyncio
import logging
import sys
import os
from sqlalchemy import select, update

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import async_session_maker
from app.models.core import Job, JobStatusEnum

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("ResetJobs")

async def reset_jobs():
    async with async_session_maker() as session:
        # Step 1: Select failed jobs
        stmt = select(Job).where(Job.status == JobStatusEnum.FAILED)
        result = await session.execute(stmt)
        failed_jobs = result.scalars().all()
        
        if not failed_jobs:
            logger.info("No FAILED jobs found to reset.")
            return

        job_ids = [j.id for j in failed_jobs]
        logger.info(f"🔄 Found {len(job_ids)} failed jobs (IDs: {job_ids}). Resetting...")

        # Step 2: Update to PENDING
        update_stmt = (
            update(Job)
            .where(Job.id.in_(job_ids))
            .values(status=JobStatusEnum.PENDING, error_message=None, assigned_printer_serial=None)
        )
        await session.execute(update_stmt)
        await session.commit()
        
        logger.info(f"✅ Resetted {len(job_ids)} jobs. The Dispatcher will pick them up in < 10s.")

if __name__ == "__main__":
    asyncio.run(reset_jobs())
