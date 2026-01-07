import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker
from app.services.job_dispatcher import job_dispatcher

async def force_dispatch():
    print("🚀 Forcing Job Dispatch cycle...")
    async with async_session_maker() as session:
        await job_dispatcher.dispatch_next_job(session)
        await session.commit()
    print("✅ Dispatch cycle finished.")

if __name__ == "__main__":
    asyncio.run(force_dispatch())
