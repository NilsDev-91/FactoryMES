import asyncio
import sys
import os

# Add parent directory to path to allow imports from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, delete
from app.core.database import async_session_maker
from app.models.core import Job, JobStatusEnum

async def purge_zombie_jobs():
    print("🔍 Scanning for zombie jobs (Status: PENDING)...")
    
    async with async_session_maker() as session:
        # 1. Find all PENDING jobs
        query = select(Job).where(Job.status == JobStatusEnum.PENDING)
        result = await session.execute(query)
        pending_jobs = result.scalars().all()
        
        if not pending_jobs:
            print("✅ No pending jobs found. The queue is clean.")
            return

        print(f"⚠️ Found {len(pending_jobs)} pending jobs:")
        for job in pending_jobs:
            print(f"   - Job ID: {job.id}, Created: {job.created_at}, GCode: {job.gcode_path}")
            
        # 2. Delete them
        print("\n🗑️  Purging pending jobs...")
        delete_query = delete(Job).where(Job.status == JobStatusEnum.PENDING)
        await session.execute(delete_query)
        await session.commit()
        
        print(f"✅ Purged {len(pending_jobs)} zombie jobs. The queue is clean.")

if __name__ == "__main__":
    # Windows Selector Event Loop Policy fix for Windows
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(purge_zombie_jobs())
